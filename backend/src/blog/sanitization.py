"""Sanityzacja HTML pochodzącego z edytora WYSIWYG.

Jedno miejsce z allowlistą tagów i atrybutów — świadomie **niezależne od
biblioteki edytora**. Edytor ogranicza to, co redaktor *może* wprowadzić;
ten moduł ogranicza to, co aplikacja *przyjmie i zwróci*. Podmiana edytora
nie przesuwa granicy bezpieczeństwa.

Sanityzujemy przy zapisie **i** przy odczycie (`.claude/rules/security.md`).
Podwójne czyszczenie nie jest nadmiarowe: do bazy da się wpisać HTML z
pominięciem `save()` — migracja danych, `bulk_create`, ręczny UPDATE,
przyszły import treści — a warstwa odczytu jest ostatnią barierą przed
`dangerouslySetInnerHTML` na froncie.
"""

from typing import Final

import nh3

#: Tagi dozwolone w treści posta.
#:
#: Bez `h1` celowo — `h1` należy do tytułu strony; drugi `h1` w treści psuje
#: strukturę nagłówków (`.claude/rules/seo.md`).
#: Bez `span`, `style` i `class` — nie dajemy redaktorowi możliwości
#: wstrzyknięcia CSS-a łamiącego layout ani kanału na `style`-based ataki.
#: Bez `iframe`/`script`/`object` — osadzenia to osobna, świadoma decyzja.
ALLOWED_TAGS: Final[frozenset[str]] = frozenset(
    {
        "p",
        "br",
        "strong",
        "em",
        "u",
        "s",
        "sub",
        "sup",
        "code",
        "pre",
        "a",
        "ul",
        "ol",
        "li",
        "h2",
        "h3",
        "h4",
        "blockquote",
        "hr",
        "figure",
        "figcaption",
        "img",
        "table",
        "thead",
        "tbody",
        "tr",
        "th",
        "td",
    }
)

#: Atrybuty dozwolone per tag. Wszystko spoza tej mapy — w tym każdy
#: handler `on*` (`onerror`, `onclick`, ...) — jest usuwane.
ALLOWED_ATTRIBUTES: Final[dict[str, set[str]]] = {
    "a": {"href", "title"},
    "img": {"src", "alt", "title", "width", "height"},
    # `type`/`data-type` to sposób, w jaki edytor zapisuje rodzaj numeracji
    # listy (1., a., i.).
    "ol": {"start", "type", "data-type"},
    "th": {"colspan", "rowspan", "scope"},
    "td": {"colspan", "rowspan"},
}

#: Schematy URL dozwolone w `href`/`src`. Brak `javascript:` i `data:`.
ALLOWED_URL_SCHEMES: Final[frozenset[str]] = frozenset({"http", "https", "mailto"})

#: `rel` dokładany do każdego linku. Nie wystawiamy `rel` jako atrybutu do
#: edycji — nh3 nadpisuje go sam, więc redaktor nie może go osłabić.
LINK_REL: Final[str] = "noopener noreferrer"

_CLEANER: Final[nh3.Cleaner] = nh3.Cleaner(
    tags=set(ALLOWED_TAGS),
    attributes={tag: set(attrs) for tag, attrs in ALLOWED_ATTRIBUTES.items()},
    url_schemes=set(ALLOWED_URL_SCHEMES),
    link_rel=LINK_REL,
    strip_comments=True,
)


def sanitize_post_html(html: str | None) -> str:
    """Zwróć HTML przepuszczony przez allowlistę.

    `None` i pusty string zwracają `""` — pole `content` nigdy nie jest
    `NULL`, a pusty edytor nie ma się zamieniać w `<p></p>`.
    """
    if not html:
        return ""
    return _CLEANER.clean(html)
