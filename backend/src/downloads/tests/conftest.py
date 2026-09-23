"""Wspólne fixture'y testów `downloads`."""

from collections.abc import Callable
from typing import Any

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from core.constants import PublicationStatus
from downloads.models import Download, DownloadTranslation


def valid_pdf(name: str = "plik.pdf") -> SimpleUploadedFile:
    """Najmniejszy plausible PDF — realna zawartość, nie tylko rozszerzenie
    (`.claude/rules/security.md`: `downloads.validators.validate_pdf_upload`
    sprawdza magic bytes)."""
    content = b"%PDF-1.4\n%mock pdf content\n"
    return SimpleUploadedFile(name, content, content_type="application/pdf")


@pytest.fixture
def make_download(db: Any) -> Callable[..., Download]:
    """Twórz `Download` z dowolnym zestawem tłumaczeń.

    Przykład: `make_download(pl={"title": "Cennik"}, en=None)` — plik bez
    wersji angielskiej.
    """

    def _make(
        *, file: Any = None, order: int = 0, **languages: dict[str, Any] | None
    ) -> Download:
        download = Download.objects.create(file=file or valid_pdf(), order=order)
        for language_code, values in languages.items():
            if values is None:
                continue
            defaults: dict[str, Any] = {
                "title": f"Tytuł {language_code}",
                "status": PublicationStatus.DRAFT,
            }
            DownloadTranslation.objects.create(
                master=download, language_code=language_code, **(defaults | values)
            )
        return download

    return _make


@pytest.fixture
def published_download(make_download: Callable[..., Download]) -> Download:
    return make_download(
        pl={"title": "Cennik badań", "status": PublicationStatus.PUBLISHED},
        en={"title": "Price list", "status": PublicationStatus.PUBLISHED},
    )


__all__ = ["make_download", "published_download", "valid_pdf"]
