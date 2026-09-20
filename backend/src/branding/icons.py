"""Ikonki SVG platform social media, wyłącznie na użytek panelu redakcyjnego.

Treść znaczników identyczna z `frontend/src/components/Header/icons/
{LinkedInIcon,InstagramIcon,FacebookIcon}.tsx` — front i admin renderują ten
sam link, więc redaktor ma widzieć tę samą ikonkę, którą zobaczy odwiedzający
stronę.

Osobny moduł zamiast stałej w `admin.py`: same znaczniki `<svg>` są
wielolinijkowe i przez to zaśmieciłyby plik admina, który poza tym jest
zwięzły (konwencja `about`/`blog`).

`_RAW_SVG_BY_PLATFORM` to stałe w kodzie, nie dane z bazy ani wejście
redaktora — `SocialPlatform` jest zamkniętą listą (`branding/models.py`), a
nowa platforma i tak wymaga tu ręcznego dopisania. `mark_safe` na tych
stałych jest więc bezpieczne, w przeciwieństwie do `mark_safe` na
niekontrolowanym wejściu.
"""

from django.utils.html import format_html
from django.utils.safestring import SafeString, mark_safe

from .models import SocialPlatform

#: Bez dynamicznego hover-koloru z frontu (tam `currentColor` reagował na
#: `:hover` w CSS) — w adminie wystarczy stały kolor, czytelny na jasnym tle
#: listy formsetów.
_ICON_COLOR = "#333333"
_ICON_SIZE = "22"

_RAW_SVG_BY_PLATFORM: dict[str, str] = {
    SocialPlatform.LINKEDIN: (
        '<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">'
        '<path d="M6.94 5a1.94 1.94 0 1 1-3.88 0 1.94 1.94 0 0 1 3.88 0Z'
        "M3.5 8.5h3.4V20H3.5V8.5Zm6.2 0h3.26v1.57h.05c.45-.86 1.56-1.76 "
        "3.22-1.76 3.44 0 4.08 2.27 4.08 5.22V20h-3.4v-5.7c0-1.36-.02-3.1"
        '-1.89-3.1-1.9 0-2.19 1.48-2.19 3v5.8H9.7V8.5Z" /></svg>'
    ),
    SocialPlatform.INSTAGRAM: (
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="1.8" aria-hidden="true">'
        '<rect x="3.5" y="3.5" width="17" height="17" rx="5" />'
        '<circle cx="12" cy="12" r="4.2" />'
        '<circle cx="17.1" cy="6.9" r="0.9" fill="currentColor" stroke="none" />'
        "</svg>"
    ),
    SocialPlatform.FACEBOOK: (
        '<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">'
        '<path d="M14.5 21v-7.2h2.4l.36-2.8h-2.76V9.18c0-.81.22-1.36 1.39-1.36'
        "h1.48V5.32c-.26-.03-1.14-.11-2.17-.11-2.15 0-3.62 1.31-3.62 3.72v2.07"
        'H9.2v2.8h2.38V21h2.92Z" /></svg>'
    ),
}


def social_platform_icon_html(platform: str) -> SafeString:
    """Znacznik `<svg>` dla platformy albo pusty string dla wartości spoza `SocialPlatform`.

    Defensywne dla nieznanego `platform` (nie powinno wystąpić przy zamkniętym
    `SocialPlatform.choices`, ale `platform` to zwykły `CharField` — wartość
    mogła trafić do bazy inną drogą niż panel, np. fixture albo przyszła
    migracja danych) — placeholder zamiast `KeyError` w widoku admina.
    """
    raw_svg = _RAW_SVG_BY_PLATFORM.get(platform)
    if raw_svg is None:
        return mark_safe("")

    sized_svg = raw_svg.replace(
        "<svg ", f'<svg width="{_ICON_SIZE}" height="{_ICON_SIZE}" ', 1
    ).replace("currentColor", _ICON_COLOR)
    # `format_html` z jednym placeholderem `{}` to standardowy wzorzec Django
    # do złożenia znanego-bezpiecznego HTML — `sized_svg` pochodzi wyłącznie
    # ze stałych w tym module, nigdy z bazy ani wejścia redaktora.
    return format_html("{}", mark_safe(sized_svg))
