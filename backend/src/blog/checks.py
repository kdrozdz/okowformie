"""Systemowe checki aplikacji `blog`.

`django-parler` bierze `choices` dla `PostTranslation.language_code` wprost
z `settings.LANGUAGES`, a kod domenowy operuje na `constants.Language`.
Rozjazd tych dwóch list jest cichy: nowy język pojawiłby się w adminie, ale
nie w logice, albo odwrotnie. Ten check zamienia go w błąd przy
`manage.py check` i w CI.
"""

from typing import Any

from django.conf import settings
from django.core.checks import Error, register

from .constants import Language

LANGUAGES_MISMATCH = "blog.E001"


@register()
def check_languages_match_settings(**kwargs: Any) -> list[Error]:
    configured = {code for code, _label in settings.LANGUAGES}
    declared = set(Language.values)

    if configured == declared:
        return []

    return [
        Error(
            "settings.LANGUAGES i blog.constants.Language opisują różne zbiory języków "
            f"({sorted(configured)} vs {sorted(declared)}).",
            hint=(
                "Dodaj język w obu miejscach naraz — settings.LANGUAGES steruje "
                "polem PostTranslation.language_code, a Language jest używany w "
                "logice bloga."
            ),
            id=LANGUAGES_MISMATCH,
        )
    ]
