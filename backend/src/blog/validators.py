"""Walidacja uploadu okładki posta.

Re-eksport z `core.validators` (`docs/decisions/2026-09-19-model-about-me.md`)
— ta sama walidacja obsługuje teraz też zdjęcie autora i skany certyfikatów
w `about`. Nazwy `validate_cover_image`/`MAX_COVER_IMAGE_BYTES` zostają, żeby
nie zmieniać dotychczasowego importu w `blog/models.py`, w migracji
`blog/migrations/0001_initial.py` (referencja do funkcji jest serializowana
po ścieżce importu) i w testach — zero zmiany zachowania, zero nowej migracji.
"""

from core.validators import ALLOWED_IMAGE_EXTENSIONS
from core.validators import MAX_IMAGE_BYTES as MAX_COVER_IMAGE_BYTES
from core.validators import validate_image_upload as validate_cover_image

__all__ = ["ALLOWED_IMAGE_EXTENSIONS", "MAX_COVER_IMAGE_BYTES", "validate_cover_image"]
