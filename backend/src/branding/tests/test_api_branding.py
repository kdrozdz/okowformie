"""Publiczne, read-only API brandingu strony (`/api/v1/branding/`).

Wzorowane na `about.tests.test_api_about` — z jedną kluczową różnicą, świadomą
i opisaną w planie (`docs/tasks/11-branding-header.md`): brak singletona w
bazie daje `200` z pustym stanem, nie `404`.
"""

from collections.abc import Callable
from io import BytesIO
from typing import Any

import pytest
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test import Client, override_settings
from django.test.utils import CaptureQueriesContext
from PIL import Image

from branding.models import SiteBranding, SocialLink, SocialPlatform

pytestmark = pytest.mark.django_db


def _valid_jpeg(name: str = "logo.jpg") -> SimpleUploadedFile:
    buffer = BytesIO()
    Image.new("RGB", (2, 2), color="red").save(buffer, format="JPEG")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/jpeg")


@pytest.fixture(autouse=True)
def _clear_throttle_cache() -> Any:
    cache.clear()
    yield
    cache.clear()


def test_brak_singletona_daje_200_z_pustym_stanem(client: Client) -> None:
    """Świadomie inaczej niż `about.views.AboutDetailView` (tamten daje 404):
    to jest konfiguracja strony, nie zasób z własnym adresem — pusty stan
    jest normalną odpowiedzią."""
    response = client.get("/api/v1/branding/")

    assert response.status_code == 200
    assert response.json() == {"logo": None, "social_links": []}


def test_singleton_bez_logo_i_bez_linkow_daje_puste_pola(
    client: Client, make_branding: Callable[..., SiteBranding]
) -> None:
    make_branding()

    body = client.get("/api/v1/branding/").json()

    assert body == {"logo": None, "social_links": []}


def test_pelny_stan_zwraca_logo_i_linki_posortowane_po_order(
    client: Client,
    make_branding: Callable[..., SiteBranding],
    make_social_link: Callable[..., SocialLink],
) -> None:
    branding = make_branding(logo=_valid_jpeg())
    make_social_link(branding, platform=SocialPlatform.FACEBOOK, order=2)
    make_social_link(branding, platform=SocialPlatform.LINKEDIN, order=0)
    make_social_link(branding, platform=SocialPlatform.INSTAGRAM, order=1)

    body = client.get("/api/v1/branding/").json()

    assert body["logo"] is not None
    assert [link["platform"] for link in body["social_links"]] == [
        "linkedin",
        "instagram",
        "facebook",
    ]
    assert body["social_links"][0] == {
        "platform": "linkedin",
        "url": "https://www.linkedin.com/in/example",
    }


@override_settings(SITE_URL="https://okowformie.pl")
def test_logo_uzywa_site_url_a_nie_hosta_zadania(
    client: Client, make_branding: Callable[..., SiteBranding]
) -> None:
    """Ten sam powód co `about.tests.test_api_about`
    (`test_zdjecia_uzywaja_site_url_a_nie_hosta_zadania`) — absolutny URL
    musi pochodzić z `settings.SITE_URL`, nie z nagłówka `Host` żądania
    (server-side fetch z innego kontenera)."""
    make_branding(logo=_valid_jpeg())

    body = client.get("/api/v1/branding/").json()

    assert body["logo"].startswith("https://okowformie.pl/media/")
    assert "testserver" not in body["logo"]


def test_naglowek_cache_control(client: Client) -> None:
    response = client.get("/api/v1/branding/")

    assert "max-age" in response.headers.get("Cache-Control", "")


def test_nie_robi_n_plus_1(
    client: Client,
    make_branding: Callable[..., SiteBranding],
    make_social_link: Callable[..., SocialLink],
) -> None:
    branding = make_branding()
    make_social_link(branding, platform=SocialPlatform.LINKEDIN, order=0)
    make_social_link(branding, platform=SocialPlatform.INSTAGRAM, order=1)
    make_social_link(branding, platform=SocialPlatform.FACEBOOK, order=2)

    with CaptureQueriesContext(connection) as queries:
        response = client.get("/api/v1/branding/")

    assert response.status_code == 200
    assert len(queries) <= 2, f"oczekiwano <=2 zapytań, było {len(queries)}: {list(queries)}"


def test_domyslny_limit_to_60_na_minute() -> None:
    from branding.throttling import BrandingAnonRateThrottle

    throttle = BrandingAnonRateThrottle()
    assert throttle.get_rate() == "60/min"


def test_przekroczony_limit_daje_429(client: Client) -> None:
    """Bije w realny, skonfigurowany limit (60/min) zamiast go podmieniać —
    ten sam wzorzec i uzasadnienie co
    `blog.tests.test_api_posts.test_przekroczony_limit_daje_429`:
    `SimpleRateThrottle.THROTTLE_RATES` jest wiązane raz, przy imporcie
    modułu, więc `override_settings`/fixture `settings` w trakcie testu nic
    tu nie zmienia. Własny scope (`branding`, `branding/throttling.py`)
    oznacza, że ten budżet jest niezależny od `about`/`posts`.
    """
    responses = [client.get("/api/v1/branding/") for _ in range(61)]

    assert [r.status_code for r in responses[:60]] == [200] * 60
    assert responses[60].status_code == 429
