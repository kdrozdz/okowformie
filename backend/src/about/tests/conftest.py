"""Wspólne fixture'y testów `about`."""

from collections.abc import Callable
from typing import Any

import pytest

from about.models import AboutMe, AboutMeTranslation, Certificate
from core.constants import PublicationStatus


@pytest.fixture
def make_about(db: Any) -> Callable[..., AboutMe]:
    """Twórz `AboutMe` z dowolnym zestawem tłumaczeń.

    Przykład: `make_about(pl={"headline": "Nagłówek"}, en=None)` — strona bez
    wersji angielskiej. Kolejne wywołania zwracają ten sam singleton
    (`AboutMe.save()` wymusza `pk=1`), więc test wywołujący to więcej niż raz
    dokłada tłumaczenia do jednego rekordu zamiast tworzyć drugi.
    """

    def _make(*, full_name: str = "Jan Kowalski", **languages: dict[str, Any] | None) -> AboutMe:
        about, _ = AboutMe.objects.get_or_create(
            pk=AboutMe.SINGLETON_ID, defaults={"full_name": full_name}
        )
        for language_code, values in languages.items():
            if values is None:
                continue
            defaults: dict[str, Any] = {
                "headline": f"Nagłówek {language_code}",
                "bio": "<p>Bio</p>",
                "status": PublicationStatus.DRAFT,
            }
            AboutMeTranslation.objects.create(
                master=about, language_code=language_code, **(defaults | values)
            )
        return about

    return _make


@pytest.fixture
def published_about(make_about: Callable[..., AboutMe]) -> AboutMe:
    return make_about(
        pl={"headline": "Optometrysta", "status": PublicationStatus.PUBLISHED},
        en={"headline": "Optometrist", "status": PublicationStatus.PUBLISHED},
    )


@pytest.fixture
def make_certificate(db: Any) -> Callable[..., Certificate]:
    def _make(about: AboutMe, **overrides: Any) -> Certificate:
        defaults: dict[str, Any] = {
            "name": "European Diploma in Optometry",
            "issuer": "ECOO",
            "issued_year": 2020,
            "order": 0,
        }
        return Certificate.objects.create(about=about, **(defaults | overrides))

    return _make
