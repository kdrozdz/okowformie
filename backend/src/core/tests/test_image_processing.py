"""Normalizacja orientacji EXIF (`core.image_processing`).

Rdzeń defektu z `docs/tasks/11-branding-header.md`: zdjęcie z telefonu ma
piksele zapisane "na leżąco" + flagę EXIF `Orientation` mówiącą, jak obrócić
przy wyświetlaniu — surowe bajty (np. favicon serwowany jako passthrough w
`app/icon.tsx`) tę flagę ignorują, więc obraz wygląda na obrócony.
"""

from io import BytesIO
from typing import Any
from unittest.mock import patch

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image, ImageOps

from core.image_processing import normalize_image_orientation


def _jpeg_with_orientation(width: int, height: int, orientation: int) -> bytes:
    """Prostokątny obraz (żeby wykryć zamianę wymiarów po obrocie) z flagą
    EXIF `Orientation` (tag 0x0112 / 274) ustawioną na `orientation`."""
    image = Image.new("RGB", (width, height), color="red")
    exif = Image.Exif()
    exif[0x0112] = orientation
    buffer = BytesIO()
    image.save(buffer, format="JPEG", exif=exif.tobytes())
    return buffer.getvalue()


def test_orientacja_6_obraca_piksele_i_usuwa_flage_exif() -> None:
    """Orientation=6 = "obróć o 90° zgodnie z ruchem wskazówek zegara" —
    prostokątny obraz 4x2 po normalizacji ma zamienione wymiary (2x4), a
    zapisany wynik nie niesie już flagi `Orientation` (ImageOps.exif_transpose
    ją usuwa po zastosowaniu obrotu)."""
    upload = SimpleUploadedFile("zdjecie.jpg", _jpeg_with_orientation(4, 2, orientation=6))

    result = normalize_image_orientation(upload)

    normalized = Image.open(result)
    assert normalized.size == (2, 4)
    assert normalized.getexif().get(0x0112) is None


def test_brak_flagi_exif_przechodzi_bez_zmiany_wymiarow() -> None:
    """Obraz bez `Orientation` (typowe dla PNG/WebP, część JPEG-ów) nie jest
    obracany — funkcja jest no-opem na wymiarach, tylko ponownie koduje plik."""
    buffer = BytesIO()
    Image.new("RGB", (4, 2), color="blue").save(buffer, format="JPEG")
    upload = SimpleUploadedFile("zdjecie.jpg", buffer.getvalue())

    result = normalize_image_orientation(upload)

    normalized = Image.open(result)
    assert normalized.size == (4, 2)


def test_zwraca_nowy_plik_bez_mutowania_wejscia() -> None:
    """Oryginalny uchwyt pliku musi zostać czytelny od początku po wywołaniu —
    ten sam wzorzec co `core.validators.validate_image_upload`, żeby dało się
    go bezpiecznie wywołać obok innych operacji na tym samym pliku w jednym
    zapisie."""
    content = _jpeg_with_orientation(4, 2, orientation=6)
    upload = SimpleUploadedFile("zdjecie.jpg", content)

    normalize_image_orientation(upload)

    upload.seek(0)
    assert upload.read() == content


def test_nazwa_wynikowego_pliku_zachowuje_rozszerzenie() -> None:
    """`upload_to` (`core.storage.RandomFilenameUploadTo`) czyta rozszerzenie
    z nazwy pliku przekazanej do `Field.pre_save` — wynik musi więc nadal
    nosić rozpoznawalną nazwę z tym samym rozszerzeniem."""
    upload = SimpleUploadedFile("zdjecie.jpg", _jpeg_with_orientation(4, 2, orientation=6))

    result = normalize_image_orientation(upload)

    assert result.name == "zdjecie.jpg"


def test_wyjatek_pillow_przy_przetwarzaniu_jest_zamieniany_na_validation_error() -> None:
    """`validate_image_upload` weryfikuje treść tylko przez `Image.verify()`,
    który nie robi pełnego decode pikseli — plik może przejść walidację, a
    mimo to wysypać dekodowanie/re-encode tutaj. Taki wyjątek Pillow ma
    wyjść jako `ValidationError`, nie surowy traceback."""
    upload = SimpleUploadedFile("zdjecie.jpg", _jpeg_with_orientation(4, 2, orientation=6))

    with (
        patch.object(ImageOps, "exif_transpose", side_effect=OSError("broken image data")),
        pytest.raises(ValidationError),
    ):
        normalize_image_orientation(upload)


def test_kontener_mpo_uzywa_jakosci_zapisu_jpeg_nie_domyslnej_pillow() -> None:
    """Telefony z podwójną kamerą/3D eksportują `.jpg` czasem jako format
    Pillow `"MPO"` — rozszerzenie przechodzi walidację, ale `image.format`
    to nie `"JPEG"`. Format zapisu musi być ustalany na podstawie
    rozszerzenia z nazwy pliku, nie introspekcji Pillow, inaczej taki plik
    dostałby domyślną (niższą) jakość Pillow zamiast `_JPEG_SAVE_QUALITY`."""
    upload = SimpleUploadedFile("logo.jpg", _jpeg_with_orientation(4, 2, orientation=6))

    original_open = Image.open

    def _open_as_mpo(*args: Any, **kwargs: Any) -> Image.Image:
        image = original_open(*args, **kwargs)
        image.format = "MPO"
        return image

    with (
        patch.object(Image, "open", side_effect=_open_as_mpo),
        patch.object(Image.Image, "save", autospec=True) as mock_save,
    ):
        normalize_image_orientation(upload)

    assert mock_save.call_args.kwargs["format"] == "JPEG"
    assert mock_save.call_args.kwargs["quality"] == 90
