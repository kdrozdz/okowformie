"""Stałe domenowe bloga.

`Language` i `PostStatus` są re-eksportem z `core.constants` (tam
`PostStatus` nazywa się `PublicationStatus` — pojęcie współdzielone z
`about`, patrz `docs/decisions/2026-09-19-model-about-me.md`). Re-eksport
zachowuje dotychczasowy import używany w `blog/` (modele, managery, admin,
testy) — zero zmiany zachowania, zero nowej migracji.
"""

from core.constants import (
    META_DESCRIPTION_MAX_LENGTH,
    META_DESCRIPTION_MIN_LENGTH,
    META_TITLE_MAX_LENGTH,
    PUBLIC_STATUS,
    Language,
)
from core.constants import PublicationStatus as PostStatus

__all__ = [
    "Language",
    "PostStatus",
    "PUBLIC_STATUS",
    "META_TITLE_MAX_LENGTH",
    "META_DESCRIPTION_MIN_LENGTH",
    "META_DESCRIPTION_MAX_LENGTH",
]
