"""Pomoce językowe współdzielone między domenami treściowymi.

Wydzielone z `blog.forms`/`about.forms` (`/code-review`, 2026-09-19) — obie
appki budowały identyczny komunikat błędu po polsku z nazwą języka, co jest
dokładnie tym ryzykiem rozjazdu, przed którym ostrzega `.claude/rules/scope.md`
(kod potrzebny w więcej niż jednej domenie trafia do `core`).
"""

from django.conf import settings


def language_label(language_code: str) -> str:
    """Nazwa języka po polsku, do wstawienia w komunikat błędu."""
    return dict(settings.LANGUAGES).get(language_code, language_code)
