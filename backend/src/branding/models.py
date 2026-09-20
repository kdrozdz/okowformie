"""Modele brandingu strony: `SiteBranding` (singleton: logo) + `SocialLink`
(lista linków social media, FK do `SiteBranding`).

Wzorowane 1:1 na `about.models.AboutMe`/`Certificate`
(`docs/tasks/11-branding-header.md`): singleton, którego `save()` wymusza
stały `pk`, i lista podrzędna edytowana przez `TabularInline` w adminie. Bez
tłumaczeń — logo i linki social media są niezależne od języka, w
przeciwieństwie do `about`/`blog` (`.claude/rules/scope.md`: treść dwujęzyczna
dotyczy treści redakcyjnej, nie brandingu strony).
"""

from typing import Any, ClassVar

from django.core.files.uploadedfile import UploadedFile
from django.db import models

from core.image_processing import normalize_image_orientation
from core.storage import RandomFilenameUploadTo
from core.validators import validate_image_upload

#: Ścieżka zapisu logo — losowa nazwa, ścieżka zawsze względna
#: (`.claude/rules/security.md`: losowe nazwy plików; `.claude/rules/scope.md`:
#: media przez abstrakcję `STORAGES`, bez ścieżek zakładających konkretny
#: backend). Współdzielona fabryka `core.storage.RandomFilenameUploadTo` —
#: patrz jej docstring dla uzasadnienia, dlaczego `blog`/`about` jej jeszcze
#: nie używają.
branding_logo_upload_to = RandomFilenameUploadTo("branding/logo")


class SiteBranding(models.Model):
    """Branding strony (logo). Singleton: zawsze `pk=1`.

    Jeden branding dla całej strony — dopuszczenie wielu rekordów tylko
    otwierałoby pole na przypadkowe duplikaty w adminie bez żadnego zysku
    (ten sam wzorzec/uzasadnienie co `about.models.AboutMe`, YAGNI).
    """

    #: Jedyny dozwolony klucz główny. `SiteBrandingAdmin.has_add_permission`
    #: blokuje próbę utworzenia drugiego rekordu z panelu; `save()` niżej
    #: pilnuje tego samego niezmiennika dla dowolnej innej ścieżki zapisu
    #: (shell, fixture, import).
    SINGLETON_ID: ClassVar[int] = 1

    logo = models.ImageField(
        verbose_name="Logo",
        upload_to=branding_logo_upload_to,
        blank=True,
        validators=[validate_image_upload],
        help_text=(
            "JPG, PNG lub WebP, maksymalnie 5 MB. Zostaw puste, żeby strona "
            "korzystała z domyślnego logo."
        ),
    )

    class Meta:
        verbose_name = "Branding strony"
        verbose_name_plural = "Branding strony"

    def __str__(self) -> str:
        return "Branding strony"

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Singleton: bez względu na to, co przyjdzie, wiersz ląduje pod `pk=1`.

        Standardowy wzorzec Django dla modeli, z których ma istnieć dokładnie
        jeden rekord — pilnuje niezmiennika niezależnie od tego, czy ktoś
        pominie panel (shell, fixture, przyszły skrypt migracyjny).

        Dodatkowo: świeżo wgrane `logo` przechodzi przez normalizację
        orientacji EXIF (`core.image_processing`) — zdjęcia z telefonu mają
        piksele zapisane "na leżąco" + flagę mówiącą, jak je obrócić, a nie
        każdy odbiorca tego samego pliku tę flagę respektuje (np. favicon
        serwowany jako surowe bajty w `frontend/src/app/icon.tsx`). Warunek
        `not self.logo._committed` odróżnia świeżo przesłany plik
        (formularz/panel) od już zapisanego pliku wczytanego ze storage przy
        zwykłym `.save()` na istniejącym rekordzie (np. zmiana tylko social
        linków) — bez tego każdy zapis ponownie kodowałby i zmieniał nazwę
        pliku loga, mimo że nikt go nie dotknął.
        """
        self.pk = self.SINGLETON_ID
        # `_committed` zamiast bezpośredniego `.logo.file`: samo odczytanie
        # `.file` na polu już zapisanym/wczytanym z bazy wymusza
        # `storage.open()` (ryzyko `FileNotFoundError`, jeśli plik zniknął ze
        # storage), mimo że logo nie jest w ogóle dotknięte przy tym zapisie.
        # `_committed` to ten sam atrybut, którego Django używa wewnętrznie w
        # `FileField.pre_save()` do tego samego rozróżnienia — prywatny (nie w
        # `django-stubs`), stąd `type: ignore` poniżej.
        is_uncommitted = not self.logo._committed  # type: ignore[attr-defined]
        if self.logo and is_uncommitted and isinstance(self.logo.file, UploadedFile):
            self.logo = normalize_image_orientation(self.logo.file)
        super().save(*args, **kwargs)


class SocialPlatform(models.TextChoices):
    """Zamknięty wybór platform social media.

    Świadome ograniczenie bezpieczeństwa, nie tymczasowa luka: redaktor nie
    ma możliwości wkleić dowolnego SVG/HTML z panelu
    (`.claude/rules/security.md`). Nowa platforma spoza tej trójki wymaga
    jednorazowej pracy developera (nowa wartość enuma + ikonka SVG we
    froncie) — patrz `docs/tasks/11-branding-header.md`.
    """

    LINKEDIN = "linkedin", "LinkedIn"
    INSTAGRAM = "instagram", "Instagram"
    FACEBOOK = "facebook", "Facebook"


class SocialLink(models.Model):
    """Jeden link do profilu social media, przypisany do brandingu strony.

    Brak linku dla danej platformy = brak wiersza, nie pusty `url` — stąd
    `url` jest wymagane, w przeciwieństwie do opcjonalnych pól obrazu w
    `about`.
    """

    branding = models.ForeignKey(
        SiteBranding,
        on_delete=models.CASCADE,
        related_name="social_links",
        verbose_name="Branding strony",
    )
    platform = models.CharField(
        verbose_name="Platforma",
        max_length=16,
        choices=SocialPlatform.choices,
        help_text="Zamknięta lista — nowa platforma wymaga zmiany w kodzie.",
    )
    url = models.URLField(
        verbose_name="Adres URL",
        help_text='Pełny adres profilu, np. „https://www.linkedin.com/in/...".',
    )
    order = models.PositiveIntegerField(
        verbose_name="Kolejność",
        default=0,
        help_text="Mniejsza liczba pokazuje się wcześniej na liście.",
    )

    class Meta:
        verbose_name = "Link social media"
        verbose_name_plural = "Linki social media"
        ordering = ["order", "id"]
        constraints = [
            # Jedna platforma raz na branding — bez tego redaktor mógłby
            # dodać dwa wiersze "linkedin" i front nie miałby jednoznacznej
            # odpowiedzi, który pokazać.
            models.UniqueConstraint(
                fields=["branding", "platform"],
                name="branding_sociallink_unique_platform_per_branding",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.get_platform_display()} ({self.url})"
