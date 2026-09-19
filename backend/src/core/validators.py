"""Walidatory uploadu obrazu, współdzielone między domenami treściowymi.

Wydzielone z `blog.validators` (`docs/decisions/2026-09-19-model-about-me.md`):
zdjęcie autora i skany certyfikatów w `about` mają dokładnie te same wymogi
co okładka posta (rozszerzenie, rozmiar) — jedna funkcja zamiast kopii.

`.claude/rules/security.md`: walidacja rozszerzenia, typu, rozmiaru **i
zawartości**; nigdy nie ufamy `Content-Type` z requestu ani samemu
rozszerzeniu. Wcześniej weryfikacja treści (Pillow) żyła wyłącznie w
automatycznym `forms.ImageField` generowanym przez `ModelForm` w adminie —
gwarancja znikała dla dowolnej innej ścieżki zapisu (shell, import, przyszłe
API zapisu), bo `Model.full_clean()` nie używa `forms.ImageField`. Ten
walidator sam otwiera i weryfikuje treść przez Pillow, więc gwarancja trzyma
się niezależnie od tego, kto go woła.

`blog.validators` re-eksportuje stąd te same nazwy pod dotychczasowymi
nazwami (`validate_cover_image`, `MAX_COVER_IMAGE_BYTES`), żeby nie zmieniać
istniejącego importu w `blog/` i importu w migracji `blog/migrations/0001_initial.py`
(referencja do funkcji jest serializowana po ścieżce importu) — zero zmiany
zachowania, zero nowej migracji.
"""

from io import BytesIO
from pathlib import Path
from typing import Final

from django.core.exceptions import ValidationError
from django.core.files.base import File
from PIL import Image

#: Formaty sensowne dla zdjęcia/skanu w panelu. Bez SVG — SVG to dokument
#: XML, który może nieść skrypt, więc nie traktujemy go jak obrazu rastrowego.
ALLOWED_IMAGE_EXTENSIONS: Final[frozenset[str]] = frozenset({".jpg", ".jpeg", ".png", ".webp"})

#: 5 MB. Powyżej tego rozmiaru obraz i tak nie nadaje się do publikacji na
#: stronie (`.claude/rules/performance.md` — budżet LCP).
MAX_IMAGE_BYTES: Final[int] = 5 * 1024 * 1024


def validate_image_upload(value: File) -> None:
    """Sprawdź rozszerzenie, rozmiar i faktyczną zawartość przesłanego obrazu."""
    extension = Path(value.name or "").suffix.lower()
    if extension not in ALLOWED_IMAGE_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_IMAGE_EXTENSIONS))
        raise ValidationError(
            "Ten format pliku nie jest obsługiwany. Zapisz obraz jako %(allowed)s "
            "i wgraj ponownie.",
            code="invalid_image_extension",
            params={"allowed": allowed},
        )

    if value.size is not None and value.size > MAX_IMAGE_BYTES:
        raise ValidationError(
            "Obraz waży %(size).1f MB, a maksimum to %(limit)d MB. "
            "Zmniejsz obraz (np. do szerokości 1600 px) i wgraj ponownie.",
            code="image_too_large",
            params={
                "size": value.size / (1024 * 1024),
                "limit": MAX_IMAGE_BYTES // (1024 * 1024),
            },
        )

    _validate_image_content(value)


def _validate_image_content(value: File) -> None:
    """Odrzuć plik, którego treść nie jest w ogóle obrazem, mimo dozwolonego
    rozszerzenia (np. skrypt zapisany jako `.jpg`).

    Weryfikacja na **kopii** wczytanej do pamięci — dokładnie ten sam wzorzec
    co `django.forms.fields.ImageField.to_python()` — bo `Image.verify()`
    psuje obiekt obrazu do dalszego użycia. Operowanie bezpośrednio na
    `value` popsułoby dalszy odczyt tego samego uchwytu pliku, gdyby ten
    walidator wykonał się więcej niż raz na tym samym pliku w tym samym
    zapisie (np. najpierw automatyczny `forms.ImageField` w adminie, potem
    ten walidator przez listę `validators=` pola modelu przy
    `instance.full_clean()`) albo gdyby po walidacji ten sam plik miał iść
    dalej do faktycznego zapisu na dysk/storage.
    """
    position = value.tell() if hasattr(value, "tell") else 0
    try:
        snapshot = BytesIO(value.read())
    finally:
        if hasattr(value, "seek"):
            value.seek(position)

    try:
        Image.open(snapshot).verify()
    except Exception as exc:
        raise ValidationError(
            "Ten plik nie jest poprawnym obrazem, mimo że rozszerzenie jest "
            "prawidłowe. Wgraj prawdziwe zdjęcie w formacie JPG, PNG lub WebP.",
            code="invalid_image_content",
        ) from exc
