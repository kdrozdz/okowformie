"""Modele strony „O mnie": `AboutMe` (singleton, wspólne) + `AboutMeTranslation`
(per język) + `Certificate` (bez tłumaczeń).

Wzorowane 1:1 na `blog.models.Post`/`PostTranslation`
(`docs/decisions/2026-09-19-model-about-me.md`), ale walidacja obrazu i
sanityzacja HTML pochodzą z `core`, nie z `blog` — `about` nie ma zależeć od
bloga (`.claude/rules/scope.md`: apps podzielone domenowo).
"""

import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar, Final

from django.db import models
from django.utils import timezone
from django_prose_editor.fields import ProseEditorField
from parler.fields import TranslationsForeignKey
from parler.models import TranslatableModel, TranslatedFieldsModel

from core.constants import META_DESCRIPTION_MAX_LENGTH, META_TITLE_MAX_LENGTH
from core.constants import PublicationStatus as AboutStatus
from core.sanitization import sanitize_html
from core.validators import validate_image_upload

from .managers import AboutMeManager
from .validators import validate_issued_year

#: Co wolno redaktorowi w edytorze WYSIWYG bio.
#:
#: Kopia `blog.models.POST_CONTENT_EXTENSIONS`, nie import — `about` nie ma
#: zależeć od `blog` (`.claude/rules/scope.md`). Dwa użycia tej samej
#: konfiguracji to jeszcze nie trzecie powtórzenie wymagające wspólnego
#: miejsca (`.claude/rules/engineering-principles.md`); gdyby doszła trzecia
#: domena treściowa z własnym WYSIWYG, wtedy przenieść do `core`.
#: Zestaw musi się **zawierać** w allowliście `core.sanitization` — pilnuje
#: tego `about/tests/test_editor_config.py`, analogicznie do bloga.
BIO_CONTENT_EXTENSIONS: Final[dict[str, Any]] = {
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


def about_photo_upload_to(instance: AboutMe, filename: str) -> str:
    """Ścieżka zapisu zdjęcia — losowa nazwa, ścieżka zawsze względna.

    Ten sam wzorzec co `blog.models.post_cover_upload_to`
    (`.claude/rules/security.md`, `.claude/rules/scope.md`: media przez
    abstrakcję `STORAGES`, bez ścieżek zakładających konkretny backend).
    """
    extension = Path(filename).suffix.lower()
    return f"about/photo/{uuid.uuid4().hex}{extension}"


def certificate_image_upload_to(instance: Certificate, filename: str) -> str:
    """Ścieżka zapisu skanu certyfikatu — losowa nazwa, ścieżka względna."""
    extension = Path(filename).suffix.lower()
    return f"about/certificates/{uuid.uuid4().hex}{extension}"


class AboutMe(TranslatableModel):
    """Strona „O mnie" — część niezależna od języka. Singleton: zawsze `pk=1`.

    Jedna, konkretna osoba (autor bloga) — dopuszczenie wielu rekordów tylko
    otwierałoby pole na przypadkowe duplikaty w adminie bez żadnego zysku
    (`docs/decisions/2026-09-19-model-about-me.md`, YAGNI).
    """

    #: Jedyny dozwolony klucz główny. `AboutMeAdmin.has_add_permission`
    #: blokuje próbę utworzenia drugiego rekordu z panelu; `save()` niżej
    #: pilnuje tego samego niezmiennika dla dowolnej innej ścieżki zapisu
    #: (shell, fixture, import).
    SINGLETON_ID: ClassVar[int] = 1

    full_name = models.CharField(
        verbose_name="Imię i nazwisko",
        max_length=200,
        help_text="Niezależne od języka — to samo w obu wersjach.",
    )
    photo = models.ImageField(
        verbose_name="Zdjęcie",
        upload_to=about_photo_upload_to,
        blank=True,
        validators=[validate_image_upload],
        help_text=(
            "JPG, PNG lub WebP, maksymalnie 5 MB. To samo zdjęcie jest używane "
            "w obu wersjach językowych — opis zdjęcia (alt) ustawiasz osobno "
            "dla każdego języka."
        ),
    )

    objects = AboutMeManager()

    if TYPE_CHECKING:
        _default_manager: ClassVar[AboutMeManager]

    class Meta:
        verbose_name = "Strona „O mnie”"
        verbose_name_plural = "Strona „O mnie”"

    def __str__(self) -> str:
        return self.full_name or "O mnie"

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Singleton: bez względu na to, co przyjdzie, wiersz ląduje pod `pk=1`.

        Standardowy wzorzec Django dla modeli, z których ma istnieć dokładnie
        jeden rekord — pilnuje niezmiennika niezależnie od tego, czy ktoś
        pominie panel (shell, fixture, przyszły skrypt migracyjny).
        """
        self.pk = self.SINGLETON_ID
        super().save(*args, **kwargs)

    def translations_by_language(self) -> dict[str, AboutMeTranslation]:
        """Mapa `kod języka -> tłumaczenie`.

        Czyta przez `self.translations.all()`, więc przy
        `prefetch_related("translations")` nie generuje dodatkowego
        zapytania — jak `blog.models.Post.translations_by_language()`.
        """
        return {translation.language_code: translation for translation in self.translations.all()}


class AboutMeTranslation(TranslatedFieldsModel):
    """Jedna wersja językowa strony „O mnie".

    Publikacja jest per język — PL może być live, gdy EN jest jeszcze
    szkicem, tak jak `blog.models.PostTranslation`.
    """

    master = TranslationsForeignKey(
        AboutMe,
        on_delete=models.CASCADE,
        related_name="translations",
        null=True,
        verbose_name="Strona „O mnie”",
    )

    headline = models.CharField(
        verbose_name="Nagłówek",
        max_length=200,
        help_text='Np. „Optometrysta, właściciel gabinetu".',
    )
    bio = ProseEditorField(
        verbose_name="Biografia",
        extensions=BIO_CONTENT_EXTENSIONS,
        blank=True,
        # `sanitize=False`: czyszczenie HTML-a robi `core.sanitization` w
        # `save()` i przy odczycie — ta sama allowlista co treść posta
        # (`blog/models.py`).
        sanitize=False,
        help_text="Formatuj przyciskami na pasku — nie musisz znać HTML-a.",
    )
    photo_alt = models.CharField(
        verbose_name="Opis zdjęcia (alt)",
        max_length=200,
        blank=True,
        help_text="Co widać na zdjęciu, jednym zdaniem. Czytają to osoby niewidome i wyszukiwarki.",
    )

    meta_title = models.CharField(
        verbose_name="Tytuł SEO",
        max_length=META_TITLE_MAX_LENGTH,
        blank=True,
        help_text=(
            f"Maksymalnie {META_TITLE_MAX_LENGTH} znaków. Zostaw puste, żeby użyć nagłówka."
        ),
    )
    meta_description = models.CharField(
        verbose_name="Opis SEO",
        max_length=META_DESCRIPTION_MAX_LENGTH,
        blank=True,
        help_text="Najlepiej 150–160 znaków. Zostaw puste, żeby użyć nagłówka.",
    )

    status = models.CharField(
        verbose_name="Status",
        max_length=16,
        choices=AboutStatus,
        default=AboutStatus.DRAFT,
        help_text=(
            "Szkic — widoczny tylko w panelu. Opublikowany — widoczny na "
            "stronie. Zarchiwizowany — zdjęty ze strony, ale treść zostaje."
        ),
    )
    published_at = models.DateTimeField(
        verbose_name="Data publikacji",
        null=True,
        blank=True,
        help_text="Uzupełnia się sama przy pierwszej publikacji.",
    )
    updated_at = models.DateTimeField(verbose_name="Ostatnia zmiana", auto_now=True)

    class Meta:
        verbose_name = "Wersja językowa strony „O mnie”"
        verbose_name_plural = "Wersje językowe strony „O mnie”"
        # Jak w abstrakcyjnym modelu `django-parler`: tłumaczeniami zarządza
        # się przez `AboutMe`, więc osobne uprawnienia tylko zaśmiecałyby
        # listę w panelu (jak `blog.models.PostTranslation.Meta`).
        default_permissions = ()
        constraints = [
            models.UniqueConstraint(
                fields=["master", "language_code"],
                name="about_aboutmetranslation_unique_language_per_about",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.headline} [{self.language_code}]"

    @property
    def bio_html(self) -> str:
        """Bio przepuszczone przez allowlistę — wersja do serializacji.

        Serializery mają sięgać tutaj, nigdy po surowe `bio`
        (`.claude/rules/security.md`).
        """
        return sanitize_html(self.bio)

    @property
    def seo_title(self) -> str:
        """`meta_title` albo nagłówek — nigdy pusty tag w HTML."""
        return self.meta_title or self.headline

    @property
    def seo_description(self) -> str:
        """`meta_description` albo nagłówek — nigdy pusty tag w HTML."""
        return self.meta_description or self.headline

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Domknij te same niezmienniki co `blog.models.PostTranslation.save()`.

        1. `bio` w bazie jest już bezpieczne — nawet jeśli ktoś ominie
           formularz (shell, import, skrypt migracyjny).
        2. Publikacja stempluje datę — status `published` bez daty byłby
           stanem niemożliwym do wyświetlenia na stronie.
        """
        self.bio = sanitize_html(self.bio)

        if self.status == AboutStatus.PUBLISHED and self.published_at is None:
            self.published_at = timezone.now()

        # Cofnięcie do szkicu/archiwum **nie** czyści `published_at` — tak
        # samo jak w `blog.models.PostTranslation.save()`.

        if (update_fields := kwargs.get("update_fields")) is not None:
            kwargs["update_fields"] = set(update_fields) | {"bio", "published_at", "updated_at"}

        super().save(*args, **kwargs)


class Certificate(models.Model):
    """Certyfikat zawodowy — bez tłumaczeń, nazwa własna jest wspólna dla PL/EN.

    Widoczność wiąże się z publikacją strony `AboutMe` w danym języku, nie z
    własnym stanem draft/published — osobny cykl redakcyjny per certyfikat
    byłby nadmiarowy dla pojedynczej, prostej listy
    (`docs/decisions/2026-09-19-model-about-me.md`).
    """

    about = models.ForeignKey(
        AboutMe,
        on_delete=models.CASCADE,
        related_name="certificates",
        verbose_name="Strona „O mnie”",
    )
    name = models.CharField(
        verbose_name="Nazwa",
        max_length=200,
        help_text='Np. „European Diploma in Optometry".',
    )
    issuer = models.CharField(
        verbose_name="Wystawca",
        max_length=200,
    )
    issued_year = models.PositiveSmallIntegerField(
        verbose_name="Rok wydania",
        validators=[validate_issued_year],
    )
    image = models.ImageField(
        verbose_name="Skan/zdjęcie certyfikatu",
        upload_to=certificate_image_upload_to,
        blank=True,
        validators=[validate_image_upload],
        help_text="Opcjonalne. JPG, PNG lub WebP, maksymalnie 5 MB.",
    )
    order = models.PositiveIntegerField(
        verbose_name="Kolejność",
        default=0,
        help_text="Mniejsza liczba pokazuje się wyżej na liście.",
    )

    class Meta:
        verbose_name = "Certyfikat"
        verbose_name_plural = "Certyfikaty"
        ordering = ["order", "id"]

    def __str__(self) -> str:
        return f"{self.name} ({self.issued_year})"
