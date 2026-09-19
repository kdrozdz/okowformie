"""Walidacja uploadu obrazu współdzielona przez `blog` i `about`.

Pełny zestaw przypadków jest już przetestowany pośrednio przez
`blog/tests/test_validators.py` (re-eksport pod `validate_cover_image`
wywołuje dokładnie tę samą funkcję) — tu smoke test kanonicznej implementacji.
"""

from io import BytesIO

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from core.validators import MAX_IMAGE_BYTES, validate_image_upload


def _valid_jpeg_bytes() -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (2, 2), color="red").save(buffer, format="JPEG")
    return buffer.getvalue()


def test_dozwolone_rozszerzenie_i_poprawna_zawartosc_przechodzi() -> None:
    validate_image_upload(SimpleUploadedFile("zdjecie.JPG", _valid_jpeg_bytes()))


def test_niedozwolone_rozszerzenie_jest_odrzucane() -> None:
    with pytest.raises(ValidationError) as error:
        validate_image_upload(SimpleUploadedFile("zdjecie.svg", b"<svg/>"))

    assert error.value.code == "invalid_image_extension"


def test_za_duzy_plik_jest_odrzucany() -> None:
    with pytest.raises(ValidationError) as error:
        validate_image_upload(SimpleUploadedFile("zdjecie.png", b"x" * (MAX_IMAGE_BYTES + 1)))

    assert error.value.code == "image_too_large"


def test_podmieniona_zawartosc_pod_dozwolonym_rozszerzeniem_jest_odrzucana() -> None:
    """Rdzeń defektu #3 (`docs/tasks/9-strona-o-mnie.md`): plik z dozwolonym
    rozszerzeniem, ale treścią, która nie jest obrazem, musi zostać odrzucony
    przez sam walidator — niezależnie od tego, czy woła go `forms.ImageField`,
    `Model.full_clean()`, czy przyszłe API zapisu."""
    with pytest.raises(ValidationError) as error:
        validate_image_upload(SimpleUploadedFile("zdjecie.jpg", b"nie jestem obrazem"))

    assert error.value.code == "invalid_image_content"


def test_walidator_nie_psuje_pliku_do_dalszego_odczytu() -> None:
    """Weryfikacja treści operuje na kopii w pamięci (`Image.verify()` psuje
    obiekt obrazu do dalszego użycia) — po walidacji oryginalny uchwyt pliku
    musi być nadal czytelny od początku, np. do faktycznego zapisu albo
    drugiego wywołania tego samego walidatora w tym samym request/save
    (np. najpierw automatyczny `forms.ImageField` w adminie, potem ten
    walidator przez listę `validators=` pola modelu)."""
    content = _valid_jpeg_bytes()
    upload = SimpleUploadedFile("zdjecie.jpg", content)

    validate_image_upload(upload)
    validate_image_upload(upload)

    upload.seek(0)
    assert upload.read() == content
