"""Modele domeny „Pliki do pobrania": `Download` (część wspólna) +
`DownloadTranslation` (per język).

Wzorowane 1:1 na `about.models.AboutMe`/`AboutMeTranslation`
(`docs/tasks/16-pliki-do-pobrania.md`): master + translation, publikacja
per język. W przeciwieństwie do `blog`/`about` — bez sluga i bez pól SEO:
plik do pobrania nie ma własnej strony szczegółu, tylko wpis na jednej
liście, więc te pola byłyby martwe.
"""

from typing import TYPE_CHECKING, Any, ClassVar

from django.db import models
from django.utils import timezone
from parler.fields import TranslationsForeignKey
from parler.models import TranslatableModel, TranslatedFieldsModel

from core.constants import PublicationStatus
from core.storage import RandomFilenameUploadTo

from .managers import DownloadManager
from .validators import validate_pdf_upload

#: Ścieżka zapisu pliku — losowa nazwa, ścieżka zawsze względna
#: (`.claude/rules/security.md`: losowe nazwy plików; `.claude/rules/scope.md`:
#: media przez abstrakcję `STORAGES`, bez ścieżek zakładających konkretny
#: backend). `downloads` to nowa domena — używa współdzielonej fabryki wprost,
#: bez legacy powodu, dla którego `blog`/`about` jej jeszcze nie używają
#: (patrz `core.storage.RandomFilenameUploadTo`, ten sam wzorzec co `branding`).
download_file_upload_to = RandomFilenameUploadTo("downloads/files")


class Download(TranslatableModel):
    """Plik do pobrania — część niezależna od języka.

    Sam plik jest wspólny dla obu wersji językowych (jeden upload, nie osobny
    per język) — decyzja wejściowa `docs/tasks/16-pliki-do-pobrania.md`.
    """

    file = models.FileField(
        verbose_name="Plik",
        upload_to=download_file_upload_to,
        validators=[validate_pdf_upload],
        help_text=(
            "Tylko PDF, maksymalnie 10 MB. Ten sam plik jest używany w obu "
            "wersjach językowych — nazwę i opis ustawiasz osobno dla każdego języka."
        ),
    )
    order = models.PositiveIntegerField(
        verbose_name="Kolejność",
        default=0,
        help_text="Mniejsza liczba pokazuje się wyżej na liście.",
    )

    objects = DownloadManager()

    if TYPE_CHECKING:
        # Analogiczny obchód co `blog.models.Post` — `django-stubs` nie
        # rozwiązuje `_default_manager` dla `TranslatableModel` bez `py.typed`.
        _default_manager: ClassVar[DownloadManager]

    class Meta:
        verbose_name = "Plik do pobrania"
        verbose_name_plural = "Pliki do pobrania"
        ordering = ["order", "id"]

    def __str__(self) -> str:
        title = self.safe_translation_getter("title", any_language=True)
        return title or f"Plik do pobrania #{self.pk}"

    def translations_by_language(self) -> dict[str, DownloadTranslation]:
        """Mapa `kod języka -> tłumaczenie`.

        Czyta przez `self.translations.all()`, więc przy
        `prefetch_related("translations")` nie generuje dodatkowego
        zapytania (`.claude/rules/performance.md`) — jak
        `blog.models.Post.translations_by_language()`.
        """
        return {translation.language_code: translation for translation in self.translations.all()}


class DownloadTranslation(TranslatedFieldsModel):
    """Jedna wersja językowa opisu pliku.

    Publikacja jest per język — PL może być live, gdy EN jest jeszcze
    szkicem, jak `blog.models.PostTranslation`.
    """

    master = TranslationsForeignKey(
        Download,
        on_delete=models.CASCADE,
        related_name="translations",
        null=True,
        verbose_name="Plik do pobrania",
    )

    title = models.CharField(
        verbose_name="Nazwa",
        max_length=200,
        help_text="Widoczna na liście plików do pobrania.",
    )
    description = models.TextField(
        verbose_name="Opis",
        blank=True,
        help_text="Opcjonalnie, kilka zdań o zawartości pliku. Zwykły tekst, bez formatowania.",
    )

    status = models.CharField(
        verbose_name="Status",
        max_length=16,
        choices=PublicationStatus,
        default=PublicationStatus.DRAFT,
        help_text=(
            "Szkic — widoczny tylko w panelu. Opublikowany — widoczny na "
            "stronie. Zarchiwizowany — zdjęty ze strony, ale plik zostaje."
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
        verbose_name = "Wersja językowa pliku do pobrania"
        verbose_name_plural = "Wersje językowe plików do pobrania"
        # Jak w abstrakcyjnym modelu `django-parler`: tłumaczeniami zarządza
        # się przez `Download`, więc osobne uprawnienia tylko zaśmiecałyby
        # listę w panelu (jak `blog.models.PostTranslation.Meta`).
        default_permissions = ()
        constraints = [
            # Jeden wiersz na (plik, język) — wymóg `django-parler`.
            models.UniqueConstraint(
                fields=["master", "language_code"],
                name="downloads_downloadtranslation_unique_language_per_download",
            ),
        ]
        indexes = [
            # Pod listę publiczną: „opublikowane w języku X" — sortowanie
            # finalne jest po `order`/`id` na mastera, nie tutaj, więc indeks
            # obejmuje tylko kolumny filtra (`.claude/rules/performance.md`).
            models.Index(
                fields=["language_code", "status"],
                name="downloads_dltr_public_list",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.title} [{self.language_code}]"

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Publikacja stempluje datę — jak `blog.models.PostTranslation.save()`.

        Cofnięcie do szkicu/archiwum **nie** czyści `published_at` — pierwotna
        data publikacji zostaje jako informacja historyczna.
        """
        if self.status == PublicationStatus.PUBLISHED and self.published_at is None:
            self.published_at = timezone.now()

        if (update_fields := kwargs.get("update_fields")) is not None:
            kwargs["update_fields"] = set(update_fields) | {"published_at", "updated_at"}

        super().save(*args, **kwargs)
