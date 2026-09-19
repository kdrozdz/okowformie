"""Sanityzacja HTML pochodzącego z edytora WYSIWYG bloga.

Re-eksport z `core.sanitization` (`docs/decisions/2026-09-19-model-about-me.md`)
— allowlista jest teraz współdzielona z `about.AboutMeTranslation.bio`. Nazwa
`sanitize_post_html` zostaje, żeby nie zmieniać dotychczasowego importu w
`blog/models.py` i w testach — zero zmiany zachowania.
"""

from core.sanitization import ALLOWED_ATTRIBUTES, ALLOWED_TAGS, ALLOWED_URL_SCHEMES, LINK_REL
from core.sanitization import sanitize_html as sanitize_post_html

__all__ = [
    "ALLOWED_TAGS",
    "ALLOWED_ATTRIBUTES",
    "ALLOWED_URL_SCHEMES",
    "LINK_REL",
    "sanitize_post_html",
]
