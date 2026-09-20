"""Niezmienniki modeli `branding`: singleton, unikalność platformy, sortowanie."""

from collections.abc import Callable
from io import BytesIO

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from PIL import Image

from branding.models import SiteBranding, SocialLink, SocialPlatform

pytestmark = pytest.mark.django_db


def _jpeg_with_orientation(width: int, height: int, orientation: int) -> bytes:
    image = Image.new("RGB", (width, height), color="red")
    exif = Image.Exif()
    exif[0x0112] = orientation
    buffer = BytesIO()
    image.save(buffer, format="JPEG", exif=exif.tobytes())
    return buffer.getvalue()


# --- Singleton --------------------------------------------------------------


def test_pierwszy_zapis_laduje_pod_pk_1() -> None:
    branding = SiteBranding.objects.create()

    assert branding.pk == SiteBranding.SINGLETON_ID


def test_kolejny_zapis_nadpisuje_ten_sam_wiersz_zamiast_tworzyc_drugi() -> None:
    """`save()` wymusza `pk=1` niezależnie od tego, jak powstaje instancja —
    nawet z pominięciem panelu (shell, fixture, import). Wzorzec identyczny z
    `about.tests.test_models.test_kolejny_zapis_nadpisuje_ten_sam_wiersz_zamiast_tworzyc_drugi`.
    """
    SiteBranding().save()
    SiteBranding().save()

    assert SiteBranding.objects.count() == 1


# --- Normalizacja orientacji EXIF loga --------------------------------------


def test_swiezo_wgrane_logo_jest_normalizowane_wg_exif() -> None:
    """Rdzeń defektu z `docs/tasks/11-branding-header.md`: zdjęcie z telefonu
    ma flagę EXIF `Orientation` mówiącą o obrocie o 90°, którą favicon
    (surowe bajty w `app/icon.tsx`) ignoruje — `save()` musi obrócić piksele
    i usunąć flagę, zanim plik trafi do storage."""
    upload = SimpleUploadedFile("logo.jpg", _jpeg_with_orientation(4, 2, orientation=6))

    branding = SiteBranding(logo=upload)
    branding.save()

    branding.refresh_from_db()
    with Image.open(branding.logo) as saved:
        assert saved.size == (2, 4)
        assert saved.getexif().get(0x0112) is None


def test_kolejny_zapis_bez_zmiany_logo_nie_przetwarza_go_ponownie(
    make_branding: Callable[..., SiteBranding],
) -> None:
    """Zapis niezwiązany z logo (np. dodanie linku social media) nie ma
    ponownie kodować i zmieniać nazwy pliku loga, mimo że nikt go nie
    dotknął — inaczej każdy zapis singletona nadawałby loga nową losową
    nazwę bez powodu."""
    branding = make_branding(logo=SimpleUploadedFile("logo.jpg", _jpeg_with_orientation(4, 2, 6)))
    logo_name_before = branding.logo.name

    branding.save()

    assert branding.logo.name == logo_name_before


def test_zapis_niedotyczacy_logo_nie_wymaga_jego_obecnosci_w_storage(
    make_branding: Callable[..., SiteBranding],
) -> None:
    """Regresja: przed fixem samo odczytanie `self.logo.file` w `save()` (przez
    `isinstance(self.logo.file, UploadedFile)`) wymuszało `storage.open()`
    nawet wtedy, gdy logo było już zapisane/wczytane z bazy, nie świeżo
    przypisane — czyli KAŻDY zapis singletona (np. edycja tylko `SocialLink`
    w inline) niepotrzebnie otwierał logo ze storage, z ryzykiem crasha, gdyby
    plik zniknął spod spodu. `save()` na instancji wczytanej z bazy (nie
    świeżo przypisane logo) nie powinien dotykać storage loga wcale."""
    branding = make_branding(logo=SimpleUploadedFile("logo.jpg", _jpeg_with_orientation(4, 2, 6)))
    logo_name = branding.logo.name
    assert logo_name is not None
    branding.logo.storage.delete(logo_name)

    reloaded = SiteBranding.objects.get(pk=SiteBranding.SINGLETON_ID)
    reloaded.save()  # nie powinno rzucić FileNotFoundError / OSError


# --- Linki social media -------------------------------------------------


def test_linki_sa_posortowane_po_order(
    make_branding: Callable[..., SiteBranding], make_social_link: Callable[..., SocialLink]
) -> None:
    branding = make_branding()
    third = make_social_link(branding, platform=SocialPlatform.FACEBOOK, order=2)
    first = make_social_link(branding, platform=SocialPlatform.LINKEDIN, order=0)
    second = make_social_link(branding, platform=SocialPlatform.INSTAGRAM, order=1)

    assert list(branding.social_links.all()) == [first, second, third]


def test_ta_sama_platforma_dwa_razy_dla_tego_samego_brandingu_jest_odrzucana(
    make_branding: Callable[..., SiteBranding], make_social_link: Callable[..., SocialLink]
) -> None:
    branding = make_branding()
    make_social_link(branding, platform=SocialPlatform.LINKEDIN)

    with pytest.raises(IntegrityError), transaction.atomic():
        make_social_link(branding, platform=SocialPlatform.LINKEDIN, url="https://linkedin.com/x")


def test_rozne_platformy_dla_tego_samego_brandingu_sa_ok(
    make_branding: Callable[..., SiteBranding], make_social_link: Callable[..., SocialLink]
) -> None:
    branding = make_branding()
    make_social_link(branding, platform=SocialPlatform.LINKEDIN)
    make_social_link(branding, platform=SocialPlatform.INSTAGRAM)

    assert branding.social_links.count() == 2


def test_url_jest_wymagany(make_branding: Callable[..., SiteBranding]) -> None:
    """Brak linku dla danej platformy to brak wiersza, nie pusty `url`
    (`docs/tasks/11-branding-header.md`)."""
    branding = make_branding()
    link = SocialLink(branding=branding, platform=SocialPlatform.LINKEDIN, url="")

    with pytest.raises(ValidationError):
        link.full_clean()
