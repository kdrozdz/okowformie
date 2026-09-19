"""Modele bloga: `Post` (część wspólna) + `PostTranslation` (per język).

Podział master + translation zamiast pól płaskich (`title_pl`, `title_en`)
jest wiążącą decyzją — `docs/decisions/2026-09-19-model-post.md`.
"""

import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar, Final

from django.conf import settings
from django.db import models
from django.utils import timezone
from django_prose_editor.fields import ProseEditorField
from parler.fields import TranslationsForeignKey
from parler.models import TranslatableModel, TranslatedFieldsModel

from .constants import (
    META_DESCRIPTION_MAX_LENGTH,
    META_TITLE_MAX_LENGTH,
    PostStatus,
)
from .managers import PostManager
from .sanitization import sanitize_post_html
from .slugs import build_unique_slug
from .validators import validate_cover_image

#: Co wolno redaktorowi w edytorze WYSIWYG.
#:
#: Zestaw jest celowo węższy niż domyślny i **zawiera się** w allowliście
#: `blog.sanitization` — to niezmiennik, który trzeba trzymać: edytor
#: pozwalający wkleić coś, co i tak zniknie przy zapisie, uczy redaktora,
#: że „panel gubi treść". Pilnuje go `tests/test_editor_config.py`.
#: Nagłówki od H2: H1 jest tytułem strony (`.claude/rules/seo.md`).
POST_CONTENT_EXTENSIONS: Final[dict[str, Any]] = {
    "Bold": True,
    "Italic": True,
    "Underline": True,
    "Strike": True,
    "Subscript": True,
    "Superscript": True,
    "Heading": {"levels": [2, 3, 4]},
    "HardBreak": True,
    "BulletList": True,
    "OrderedList": True,
    "ListItem": True,
    "Blockquote": True,
    "HorizontalRule": True,
    "Code": True,
    "CodeBlock": True,
    "Table": True,
    "TableRow": True,
    "TableHeader": True,
    "TableCell": True,
    "Link": {"enableTarget": False, "protocols": ["http", "https", "mailto"]},
    "History": True,
    "HTML": True,
    "Typographic": True,
}


def post_cover_upload_to(instance: Post, filename: str) -> str:
    """Ścieżka zapisu okładki — losowa nazwa, ścieżka zawsze względna.

    Losowa nazwa (`.claude/rules/security.md`) zamyka zgadywanie adresów i
    nadpisywanie cudzych plików nazwą. Ścieżka jest względna, więc backend
    storage da się podmienić (VPS → S3) bez migracji danych w modelu.
    """
    extension = Path(filename).suffix.lower()
    return f"blog/covers/{uuid.uuid4().hex}{extension}"


class Post(TranslatableModel):
    """Post bloga — część niezależna od języka."""

    cover_image = models.ImageField(
        verbose_name="Obraz okładki",
        upload_to=post_cover_upload_to,
        blank=True,
        validators=[validate_cover_image],
        help_text=(
            "JPG, PNG lub WebP, maksymalnie 5 MB. Ten sam obraz jest używany "
            "w obu wersjach językowych — opis obrazu (alt) ustawiasz osobno "
            "dla każdego języka."
        ),
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        # PROTECT, nie CASCADE: skasowanie konta redaktora nie może zabrać
        # ze sobą treści bloga. Usunięcie autora wymaga świadomego
        # przepięcia postów na inne konto.
        on_delete=models.PROTECT,
        related_name="posts",
        verbose_name="Autor",
    )
    created_at = models.DateTimeField(verbose_name="Data utworzenia", auto_now_add=True)

    objects = PostManager()

    if TYPE_CHECKING:
        # `TranslatableModel` z parlera nie ma `py.typed`, więc wtyczka
        # `django-stubs` nie dopisuje Postowi `_default_manager` i nie
        # potrafi rozwiązać relacji odwrotnej `User.posts`. Deklaracja
        # tylko dla typów; w runtime robi to Django.
        _default_manager: ClassVar[PostManager]

    class Meta:
        verbose_name = "Post"
        verbose_name_plural = "Posty"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        title = self.safe_translation_getter("title", any_language=True)
        return title or f"Post #{self.pk}"

    def translations_by_language(self) -> dict[str, PostTranslation]:
        """Mapa `kod języka -> tłumaczenie`.

        Czyta przez `self.translations.all()`, więc przy
        `prefetch_related("translations")` nie generuje zapytania na post —
        to jest warunek, żeby kolumny statusów na liście w adminie nie
        zrobiły N+1 (`.claude/rules/performance.md`).
        """
        return {translation.language_code: translation for translation in self.translations.all()}


class PostTranslation(TranslatedFieldsModel):
    """Jedna wersja językowa posta.

    Tu leżą `status` i `published_at`, bo publikacja jest per język: PL może
    być live, gdy EN jest jeszcze szkicem.

    Pole języka to parlerowe `language_code` (nie własne `language`) —
    biblioteka buduje na nim całe API tłumaczeń, a `choices` bierze z
    `settings.LANGUAGES`. Własna nazwa oznaczałaby walkę z biblioteką bez
    zysku.
    """

    # `TranslationsForeignKey`, nie zwykły `ForeignKey`: to podklasa FK o tym
    # samym kształcie w bazie, ale rejestrująca tłumaczenia na modelu
    # nadrzędnym. Bez niej migracje danych (np. przyszłe przenumerowanie
    # slugów) nie widzą pól tłumaczonych — parler ostrzega o tym wprost.
    master = TranslationsForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name="translations",
        null=True,
        verbose_name="Post",
    )

    title = models.CharField(
        verbose_name="Tytuł",
        max_length=200,
        help_text="Widoczny na liście postów i jako nagłówek H1 strony.",
    )
    slug = models.SlugField(
        verbose_name="Adres URL (slug)",
        max_length=220,
        blank=True,
        help_text=(
            "Końcówka adresu strony. Zostaw puste — uzupełni się z tytułu. "
            "Po opublikowaniu lepiej go nie zmieniać: stary adres przestanie działać."
        ),
    )
    excerpt = models.CharField(
        verbose_name="Zajawka",
        max_length=400,
        help_text=(
            "Dwa–trzy zdania streszczenia. Pokazuje się na liście postów i "
            "zastępuje opis SEO, jeśli go nie wypełnisz."
        ),
    )
    content = ProseEditorField(
        verbose_name="Treść",
        extensions=POST_CONTENT_EXTENSIONS,
        blank=True,
        # `sanitize=False`: czyszczenie HTML-a robi `blog.sanitization` w
        # `save()` i przy odczycie, jedną allowlistą niezależną od edytora.
        # Dwa niezależne filtry oznaczałyby dwie prawdy o tym, co wolno.
        sanitize=False,
        help_text="Formatuj przyciskami na pasku — nie musisz znać HTML-a.",
    )
    cover_image_alt = models.CharField(
        verbose_name="Opis obrazu okładki (alt)",
        max_length=200,
        blank=True,
        help_text=(
            "Co widać na obrazku, jednym zdaniem. Czytają to osoby niewidome i wyszukiwarki."
        ),
    )

    meta_title = models.CharField(
        verbose_name="Tytuł SEO",
        max_length=META_TITLE_MAX_LENGTH,
        blank=True,
        help_text=(
            f"Maksymalnie {META_TITLE_MAX_LENGTH} znaków. Zostaw puste, żeby użyć tytułu posta."
        ),
    )
    meta_description = models.CharField(
        verbose_name="Opis SEO",
        max_length=META_DESCRIPTION_MAX_LENGTH,
        blank=True,
        help_text=("Najlepiej 150–160 znaków. Zostaw puste, żeby użyć zajawki."),
    )

    status = models.CharField(
        verbose_name="Status",
        max_length=16,
        choices=PostStatus,
        default=PostStatus.DRAFT,
        help_text=(
            "Szkic — widoczny tylko w panelu. Opublikowany — widoczny na "
            "stronie. Zarchiwizowany — zdjęty ze strony, ale treść zostaje."
        ),
    )
    published_at = models.DateTimeField(
        verbose_name="Data publikacji",
        null=True,
        blank=True,
        help_text=(
            "Uzupełnia się sama przy pierwszej publikacji. Zmień tylko, jeśli "
            "chcesz pokazać inną datę."
        ),
    )
    updated_at = models.DateTimeField(verbose_name="Ostatnia zmiana", auto_now=True)

    class Meta:
        verbose_name = "Wersja językowa posta"
        verbose_name_plural = "Wersje językowe postów"
        # Jak w abstrakcyjnym modelu `django-parler`: tłumaczeniami zarządza
        # się przez `Post`, więc osobne uprawnienia tylko zaśmiecałyby listę
        # w panelu.
        default_permissions = ()
        constraints = [
            # Jeden wiersz na (post, język) — wymóg `django-parler`.
            models.UniqueConstraint(
                fields=["master", "language_code"],
                name="blog_posttranslation_unique_language_per_post",
            ),
            # Slug unikalny **w obrębie języka**, nie globalnie: ten sam
            # slug może istnieć w PL i w EN (`.claude/rules/performance.md`).
            models.UniqueConstraint(
                fields=["language_code", "slug"],
                name="blog_posttranslation_unique_slug_per_language",
            ),
        ]
        indexes = [
            # Pod listę publiczną: „opublikowane w języku X, najnowsze
            # pierwsze". Kolejność kolumn odpowiada selektywności zapytania
            # (równość, równość, sortowanie).
            models.Index(
                fields=["language_code", "status", "-published_at"],
                name="blog_posttr_public_list",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.title} [{self.language_code}]"

    @property
    def content_html(self) -> str:
        """Treść przepuszczona przez allowlistę — to wersja do serializacji.

        Serializery i szablony mają sięgać tutaj, nigdy po surowe
        `content` (`.claude/rules/security.md`).
        """
        return sanitize_post_html(self.content)

    @property
    def seo_title(self) -> str:
        """`meta_title` albo tytuł — nigdy pusty tag w HTML."""
        return self.meta_title or self.title

    @property
    def seo_description(self) -> str:
        """`meta_description` albo zajawka — nigdy pusty tag w HTML."""
        return self.meta_description or self.excerpt

    def generate_slug(self) -> str:
        """Wolny slug wyprowadzony z tytułu, unikalny w obrębie języka."""
        max_length: int = self._meta.get_field("slug").max_length  # type: ignore[assignment]

        def is_taken(candidate: str) -> bool:
            taken = PostTranslation.objects.filter(language_code=self.language_code, slug=candidate)
            if self.pk:
                taken = taken.exclude(pk=self.pk)
            return taken.exists()

        return build_unique_slug(self.title, is_taken=is_taken, max_length=max_length)

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Domknij trzy niezmienniki, zanim wiersz trafi do bazy.

        1. `content` w bazie jest już bezpieczny — nawet jeśli ktoś ominie
           formularz (shell, import, skrypt migracyjny).
        2. Slug istnieje zawsze; redaktor nigdy nie musi go wpisywać ręcznie
           (`.claude/rules/content-admin.md`).
        3. Publikacja stempluje datę — status `published` bez daty byłby
           stanem niemożliwym do posortowania na liście publicznej.
        """
        self.content = sanitize_post_html(self.content)

        if not self.slug:
            self.slug = self.generate_slug()

        if self.status == PostStatus.PUBLISHED and self.published_at is None:
            self.published_at = timezone.now()

        # Cofnięcie do szkicu/archiwum **nie** czyści `published_at` —
        # pierwotna data publikacji to informacja historyczna, a post
        # przywrócony na stronę ma wrócić z tą samą datą.

        if (update_fields := kwargs.get("update_fields")) is not None:
            kwargs["update_fields"] = set(update_fields) | {
                "content",
                "slug",
                "published_at",
                "updated_at",
            }

        super().save(*args, **kwargs)
