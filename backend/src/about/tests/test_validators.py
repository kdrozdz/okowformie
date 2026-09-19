"""Walidacja roku wydania certyfikatu."""

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from about.validators import MIN_ISSUED_YEAR, validate_issued_year


def test_rok_ponizej_minimum_jest_odrzucany() -> None:
    with pytest.raises(ValidationError) as error:
        validate_issued_year(MIN_ISSUED_YEAR - 1)

    assert error.value.code == "invalid_issued_year"


def test_rok_w_przyszlosci_jest_odrzucany() -> None:
    with pytest.raises(ValidationError) as error:
        validate_issued_year(timezone.now().year + 1)

    assert error.value.code == "invalid_issued_year"


def test_minimalny_rok_przechodzi() -> None:
    validate_issued_year(MIN_ISSUED_YEAR)


def test_biezacy_rok_przechodzi() -> None:
    validate_issued_year(timezone.now().year)
