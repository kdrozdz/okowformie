"""Walidacja uploadu okładki (`.claude/rules/security.md`)."""

from io import BytesIO

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from blog.validators import MAX_COVER_IMAGE_BYTES, validate_cover_image


def _valid_jpeg_bytes() -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (2, 2), color="red").save(buffer, format="JPEG")
    return buffer.getvalue()


def test_dozwolone_rozszerzenie_i_poprawna_zawartosc_przechodzi() -> None:
    validate_cover_image(SimpleUploadedFile("okladka.JPG", _valid_jpeg_bytes()))


def test_svg_jest_odrzucany() -> None:
    """SVG to dokument XML, nie obraz rastrowy — może nieść skrypt."""
    with pytest.raises(ValidationError) as error:
        validate_cover_image(SimpleUploadedFile("okladka.svg", b"<svg/>"))

    assert error.value.code == "invalid_image_extension"


def test_zmiana_rozszerzenia_nie_omija_kontroli() -> None:
    with pytest.raises(ValidationError):
        validate_cover_image(SimpleUploadedFile("skrypt.php", b"<?php"))


def test_za_duzy_plik_jest_odrzucany() -> None:
    with pytest.raises(ValidationError) as error:
        validate_cover_image(SimpleUploadedFile("okladka.png", b"x" * (MAX_COVER_IMAGE_BYTES + 1)))

    assert error.value.code == "image_too_large"


def test_podmieniona_zawartosc_pod_dozwolonym_rozszerzeniem_jest_odrzucana() -> None:
    """`validate_cover_image` re-eksportuje `core.validators.validate_image_upload`
    — ten sam test jak `core/tests/test_validators.py`, tu jako regresja pod
    dotychczasową nazwą używaną przez `blog/models.py`."""
    with pytest.raises(ValidationError) as error:
        validate_cover_image(SimpleUploadedFile("okladka.jpg", b"nie jestem obrazem"))

    assert error.value.code == "invalid_image_content"
