"""Walidatory uploadu obrazu okładki.

`.claude/rules/security.md`: walidacja rozszerzenia, typu i rozmiaru;
nigdy nie ufamy `Content-Type` z requestu. `ImageField` dokłada do tego
weryfikację przez Pillow (plik musi dać się otworzyć jako obraz), więc
podmieniona nazwa nie przepuści pliku wykonywalnego.
"""

from pathlib import Path
from typing import Final

from django.core.exceptions import ValidationError
from django.core.files.base import File

#: Formaty sensowne dla okładki wpisu. Bez SVG — SVG to dokument XML,
#: który może nieść skrypt, więc nie traktujemy go jak obrazu rastrowego.
ALLOWED_IMAGE_EXTENSIONS: Final[frozenset[str]] = frozenset({".jpg", ".jpeg", ".png", ".webp"})

#: 5 MB. Powyżej tego rozmiaru obraz i tak nie nadaje się na okładkę
#: (`.claude/rules/performance.md` — budżet LCP).
MAX_COVER_IMAGE_BYTES: Final[int] = 5 * 1024 * 1024


def validate_cover_image(value: File) -> None:
    """Sprawdź rozszerzenie i rozmiar pliku okładki."""
    extension = Path(value.name or "").suffix.lower()
    if extension not in ALLOWED_IMAGE_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_IMAGE_EXTENSIONS))
        raise ValidationError(
            "Ten format pliku nie jest obsługiwany. Zapisz obraz jako %(allowed)s "
            "i wgraj ponownie.",
            code="invalid_image_extension",
            params={"allowed": allowed},
        )

    if value.size is not None and value.size > MAX_COVER_IMAGE_BYTES:
        raise ValidationError(
            "Obraz waży %(size).1f MB, a maksimum to %(limit)d MB. "
            "Zmniejsz obraz (np. do szerokości 1600 px) i wgraj ponownie.",
            code="image_too_large",
            params={
                "size": value.size / (1024 * 1024),
                "limit": MAX_COVER_IMAGE_BYTES // (1024 * 1024),
            },
        )
