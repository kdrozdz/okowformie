"""Publiczne, read-only API strony „O mnie" (`/api/v1/{lang}/about/`).

Widoczność (draft/archived, brak tłumaczenia) jest już przetestowana na
poziomie managera w `test_managers.py`; tutaj sprawdzamy, że API **korzysta**
z tych granic i poprawnie tłumaczy je na kody HTTP/kształt odpowiedzi —
analogicznie do `blog/tests/test_api_posts.py`.
"""

from collections.abc import Callable
from typing import Any

import pytest
from django.core.cache import cache
from django.db import connection
from django.test import Client
from django.test.utils import CaptureQueriesContext

from about.models import AboutMe, Certificate
from core.constants import PublicationStatus

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _clear_throttle_cache() -> Any:
    cache.clear()
    yield
    cache.clear()


def test_brak_singletona_daje_404(client: Client) -> None:
    response = client.get("/api/v1/pl/about/")

    assert response.status_code == 404


def test_szkic_daje_404(client: Client, make_about: Callable[..., AboutMe]) -> None:
    make_about(pl={"status": PublicationStatus.DRAFT})

    response = client.get("/api/v1/pl/about/")

    assert response.status_code == 404


def test_archiwum_daje_404(client: Client, make_about: Callable[..., AboutMe]) -> None:
    make_about(pl={"status": PublicationStatus.ARCHIVED})

    response = client.get("/api/v1/pl/about/")

    assert response.status_code == 404


def test_brak_tlumaczenia_en_daje_404_nie_polska_tresc(
    client: Client, make_about: Callable[..., AboutMe]
) -> None:
    make_about(pl={"status": PublicationStatus.PUBLISHED}, en=None)

    response = client.get("/api/v1/en/about/")

    assert response.status_code == 404


def test_zly_lang_daje_404(client: Client, make_about: Callable[..., AboutMe]) -> None:
    make_about(pl={"status": PublicationStatus.PUBLISHED})

    response = client.get("/api/v1/de/about/")

    assert response.status_code == 404


def test_opublikowana_strona_zwraca_pola(
    client: Client, make_about: Callable[..., AboutMe]
) -> None:
    make_about(
        pl={
            "headline": "Optometrysta",
            "bio": "<p>Cześć</p>",
            "status": PublicationStatus.PUBLISHED,
        },
        en={"headline": "Optometrist", "status": PublicationStatus.PUBLISHED},
    )

    body = client.get("/api/v1/pl/about/").json()

    assert body["full_name"] == "Jan Kowalski"
    assert body["headline"] == "Optometrysta"
    assert "<p>Cześć</p>" in body["bio"]
    assert body["photo"] is None
    assert body["certificates"] == []
    assert body["available_translations"] == [{"language": "en"}, {"language": "pl"}]


def test_bio_jest_sanityzowane(client: Client, make_about: Callable[..., AboutMe]) -> None:
    make_about(
        pl={
            "status": PublicationStatus.PUBLISHED,
            "bio": '<p>Ok</p><script>alert("xss")</script><img src="x" onerror="alert(1)">',
        }
    )

    body = client.get("/api/v1/pl/about/").json()

    assert "<script" not in body["bio"]
    assert "onerror" not in body["bio"]
    assert "<p>Ok</p>" in body["bio"]


def test_niepublikowane_tlumaczenie_nie_wchodzi_do_available_translations(
    client: Client, make_about: Callable[..., AboutMe]
) -> None:
    make_about(
        pl={"status": PublicationStatus.PUBLISHED},
        en={"status": PublicationStatus.DRAFT},
    )

    body = client.get("/api/v1/pl/about/").json()

    assert body["available_translations"] == [{"language": "pl"}]


def test_puste_pola_seo_maja_fallback_na_naglowek(
    client: Client, make_about: Callable[..., AboutMe]
) -> None:
    make_about(
        pl={
            "headline": "Nagłówek bez SEO",
            "status": PublicationStatus.PUBLISHED,
            "meta_title": "",
            "meta_description": "",
        }
    )

    body = client.get("/api/v1/pl/about/").json()

    assert body["meta_title"] == "Nagłówek bez SEO"
    assert body["meta_description"] == "Nagłówek bez SEO"


def test_certyfikaty_sa_posortowane_po_order(
    client: Client,
    make_about: Callable[..., AboutMe],
    make_certificate: Callable[..., Certificate],
) -> None:
    about = make_about(pl={"status": PublicationStatus.PUBLISHED})
    make_certificate(about, name="Trzeci", order=2)
    make_certificate(about, name="Pierwszy", order=0)
    make_certificate(about, name="Drugi", order=1)

    body = client.get("/api/v1/pl/about/").json()

    assert [c["name"] for c in body["certificates"]] == ["Pierwszy", "Drugi", "Trzeci"]


def test_certyfikat_bez_zdjecia_daje_null(
    client: Client,
    make_about: Callable[..., AboutMe],
    make_certificate: Callable[..., Certificate],
) -> None:
    about = make_about(pl={"status": PublicationStatus.PUBLISHED})
    make_certificate(about)

    body = client.get("/api/v1/pl/about/").json()

    assert body["certificates"][0]["image"] is None


def test_naglowek_cache_control(client: Client, make_about: Callable[..., AboutMe]) -> None:
    make_about(pl={"status": PublicationStatus.PUBLISHED})

    response = client.get("/api/v1/pl/about/")

    assert "max-age" in response.headers.get("Cache-Control", "")


def test_nie_robi_n_plus_1(
    client: Client,
    make_about: Callable[..., AboutMe],
    make_certificate: Callable[..., Certificate],
) -> None:
    about = make_about(
        pl={"status": PublicationStatus.PUBLISHED},
        en={"status": PublicationStatus.PUBLISHED},
    )
    for index in range(5):
        make_certificate(about, name=f"Certyfikat {index}", order=index)

    with CaptureQueriesContext(connection) as queries:
        response = client.get("/api/v1/pl/about/")

    assert response.status_code == 200
    assert len(queries) <= 3, f"oczekiwano <=3 zapytań, było {len(queries)}: {list(queries)}"


def test_domyslny_limit_to_60_na_minute() -> None:
    from about.throttling import AboutAnonRateThrottle

    throttle = AboutAnonRateThrottle()
    assert throttle.get_rate() == "60/min"
