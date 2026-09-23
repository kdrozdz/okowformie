"""Walidacja uploadu pliku do pobrania (`downloads/validators.py`)."""

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile

from downloads.validators import MAX_FILE_BYTES, validate_pdf_upload


def _pdf(
    content: bytes = b"%PDF-1.4\n%mock pdf content\n", name: str = "plik.pdf"
) -> SimpleUploadedFile:
    return SimpleUploadedFile(name, content, content_type="application/pdf")


def test_zly_format_rozszerzenia_jest_odrzucany() -> None:
    upload = SimpleUploadedFile("plik.txt", b"%PDF-1.4\n", content_type="text/plain")

    with pytest.raises(ValidationError) as error:
        validate_pdf_upload(upload)

    assert error.value.code == "invalid_file_extension"


def test_falszywa_zawartosc_mimo_rozszerzenia_pdf_jest_odrzucana() -> None:
    """Rozszerzenie `.pdf`, ale realna treść to zwykły tekst — nie ufamy
    samemu rozszerzeniu (`.claude/rules/security.md`)."""
    upload = _pdf(content=b"to nie jest pdf, tylko zwykly tekst")

    with pytest.raises(ValidationError) as error:
        validate_pdf_upload(upload)

    assert error.value.code == "invalid_file_content"


def test_za_duzy_plik_jest_odrzucany() -> None:
    content = b"%PDF-1.4\n" + b"0" * (MAX_FILE_BYTES + 1)
    upload = _pdf(content=content)

    with pytest.raises(ValidationError) as error:
        validate_pdf_upload(upload)

    assert error.value.code == "file_too_large"


def test_prawdziwy_pdf_przechodzi() -> None:
    upload = _pdf()

    validate_pdf_upload(upload)  # nie podnosi wyjątku
