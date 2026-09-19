"""Walidacja pól specyficznych dla `about` (nieprzenaszalna do `core`).

Walidacja obrazu (`photo`, `Certificate.image`) korzysta wprost z
`core.validators.validate_image_upload` — to jest współdzielone z `blog`, więc
mieszka w `core` (`docs/decisions/2026-09-19-model-about-me.md`). Rok
wydania certyfikatu jest natomiast pojęciem wyłącznie tej aplikacji.
"""

from typing import Final

from django.core.exceptions import ValidationError
from django.utils import timezone

#: Najstarszy sensowny rok wydania certyfikatu zawodowego. Wcześniej nie
#: istniały jeszcze żadne z uznawanych dziś kwalifikacji optometrycznych.
MIN_ISSUED_YEAR: Final[int] = 1950


def validate_issued_year(value: int) -> None:
    """Rok musi mieścić się między `MIN_ISSUED_YEAR` a bieżącym rokiem.

    Sprawdzane dynamicznie względem `timezone.now()`, nie stałą górną
    granicą wpisaną raz na zawsze — certyfikat wystawiony "w przyszłości"
    nie ma sensu.
    """
    current_year = timezone.now().year
    if value < MIN_ISSUED_YEAR or value > current_year:
        raise ValidationError(
            "Podaj rok wydania między %(min)d a %(max)d.",
            code="invalid_issued_year",
            params={"min": MIN_ISSUED_YEAR, "max": current_year},
        )
