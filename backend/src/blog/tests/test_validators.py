"""Walidacja uploadu okładki (`.claude/rules/security.md`)."""

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile

from blog.validators import MAX_COVER_IMAGE_BYTES, validate_cover_image


def test_dozwolone_rozszerzenie_przechodzi() -> None:
    validate_cover_image(SimpleUploadedFile("okladka.JPG", b"x"))


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
