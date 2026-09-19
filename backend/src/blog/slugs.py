"""Generowanie slugów z polskich tytułów.

Django `slugify()` normalizuje przez NFKD i odrzuca to, czego nie da się
sprowadzić do ASCII. Dla większości polskich znaków działa to dobrze
(`ą` → `a`), ale `ł`/`Ł` nie mają dekompozycji i **znikają bez śladu** —
„Żółty młyn" dałoby `zoty-myn`. Dlatego transliterujemy jawnie, zanim
oddamy tekst Django.
"""

from collections.abc import Callable
from typing import Final

from django.utils.text import slugify

_POLISH_TRANSLITERATION: Final[dict[int, str]] = str.maketrans(
    {
        "ą": "a",
        "ć": "c",
        "ę": "e",
        "ł": "l",
        "ń": "n",
        "ó": "o",
        "ś": "s",
        "ź": "z",
        "ż": "z",
        "Ą": "A",
        "Ć": "C",
        "Ę": "E",
        "Ł": "L",
        "Ń": "N",
        "Ó": "O",
        "Ś": "S",
        "Ź": "Z",
        "Ż": "Z",
    }
)

#: Używany, gdy z tytułu nie da się wycisnąć ani jednego znaku slugu
#: (tytuł złożony wyłącznie z interpunkcji albo z pisma niełacińskiego).
FALLBACK_SLUG: Final[str] = "post"


def slugify_pl(value: str) -> str:
    """Zamień tytuł na slug, zachowując polskie znaki jako ich odpowiedniki ASCII."""
    return slugify(value.translate(_POLISH_TRANSLITERATION))


def build_unique_slug(
    source: str,
    *,
    is_taken: Callable[[str], bool],
    max_length: int,
) -> str:
    """Zbuduj slug z `source`, doklejając `-2`, `-3`, ... aż będzie wolny.

    `is_taken` decyduje o zajętości — dzięki temu ta funkcja nie wie nic o
    ORM-ie i daje się przetestować bez bazy. Wołający zawęża sprawdzenie do
    jednego języka (slug jest unikalny w obrębie języka, nie globalnie).
    """
    base = slugify_pl(source)[:max_length] or FALLBACK_SLUG

    candidate = base
    suffix = 2
    while is_taken(candidate):
        tail = f"-{suffix}"
        candidate = f"{base[: max_length - len(tail)]}{tail}"
        suffix += 1
    return candidate
