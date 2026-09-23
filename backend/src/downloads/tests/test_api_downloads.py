"""Publiczne, read-only API plików do pobrania (`/api/v1/{lang}/downloads/`).

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
from django.test import Client, override_settings
from django.test.utils import CaptureQueriesContext

from core.constants import PublicationStatus
from downloads.models import Download

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _clear_throttle_cache() -> Any:
    """Throttling trzyma stan w cache (Redis) — nie ma zniknąć między testami."""
    cache.clear()
    yield
    cache.clear()


def test_pusta_lista_daje_200_i_pusty_wynik(client: Client) -> None:
    response = client.get("/api/v1/pl/downloads/")

    assert response.status_code == 200
    assert response.json()["results"] == []


def test_lista_pokazuje_tylko_opublikowane(
    client: Client, make_download: Callable[..., Download]
) -> None:
    make_download(pl={"title": "Szkic", "status": PublicationStatus.DRAFT})
    make_download(pl={"title": "Archiwum", "status": PublicationStatus.ARCHIVED})
    make_download(pl={"title": "Widoczny", "status": PublicationStatus.PUBLISHED})

    response = client.get("/api/v1/pl/downloads/")

    titles = [item["title"] for item in response.json()["results"]]
    assert titles == ["Widoczny"]


def test_lista_zwraca_pola(client: Client, make_download: Callable[..., Download]) -> None:
    make_download(
        order=3,
        pl={
            "title": "Cennik badań",
            "description": "Aktualny cennik badań wzroku.",
            "status": PublicationStatus.PUBLISHED,
        },
    )

    item = client.get("/api/v1/pl/downloads/").json()["results"][0]

    assert item["title"] == "Cennik badań"
    assert item["description"] == "Aktualny cennik badań wzroku."
    assert item["order"] == 3
    assert item["file"].startswith("http")
    assert set(item) == {"title", "description", "file", "order"}


def test_lista_jest_posortowana_po_order(
    client: Client, make_download: Callable[..., Download]
) -> None:
    make_download(order=2, pl={"title": "Trzeci", "status": PublicationStatus.PUBLISHED})
    make_download(order=0, pl={"title": "Pierwszy", "status": PublicationStatus.PUBLISHED})
    make_download(order=1, pl={"title": "Drugi", "status": PublicationStatus.PUBLISHED})

    titles = [item["title"] for item in client.get("/api/v1/pl/downloads/").json()["results"]]

    assert titles == ["Pierwszy", "Drugi", "Trzeci"]


def test_paginacja_dziala(client: Client, make_download: Callable[..., Download]) -> None:
    """Domyślny `PAGE_SIZE=20` z globalnych ustawień DRF — `downloads` celowo
    nie nadpisuje go własną klasą paginacji (`downloads/views.py`)."""
    for index in range(25):
        make_download(
            order=index, pl={"title": f"Plik {index}", "status": PublicationStatus.PUBLISHED}
        )

    first_page = client.get("/api/v1/pl/downloads/").json()
    second_page = client.get("/api/v1/pl/downloads/?page=2").json()

    assert len(first_page["results"]) == 20
    assert len(second_page["results"]) == 5
    assert first_page["count"] == 25


def test_brak_tlumaczenia_en_nie_wypada_na_polska_tresc(
    client: Client, make_download: Callable[..., Download]
) -> None:
    make_download(pl={"title": "Tylko PL", "status": PublicationStatus.PUBLISHED}, en=None)

    response = client.get("/api/v1/en/downloads/")

    assert response.json()["results"] == []


def test_zly_lang_daje_404(client: Client, make_download: Callable[..., Download]) -> None:
    make_download(pl={"status": PublicationStatus.PUBLISHED})

    response = client.get("/api/v1/de/downloads/")

    assert response.status_code == 404


@override_settings(SITE_URL="https://okowformie.pl")
def test_plik_uzywa_site_url_a_nie_hosta_zadania(
    client: Client, make_download: Callable[..., Download]
) -> None:
    """Analogicznie do `blog`/`about`: absolutny URL pliku ma pochodzić z
    `settings.SITE_URL`, nie z nagłówka `Host` żądania (test client domyślnie
    woła `testserver`)."""
    make_download(pl={"status": PublicationStatus.PUBLISHED})

    item = client.get("/api/v1/pl/downloads/").json()["results"][0]

    assert item["file"].startswith("https://okowformie.pl/media/")
    assert "testserver" not in item["file"]


def test_naglowek_cache_control(client: Client, make_download: Callable[..., Download]) -> None:
    make_download(pl={"status": PublicationStatus.PUBLISHED})

    response = client.get("/api/v1/pl/downloads/")

    assert "max-age" in response.headers.get("Cache-Control", "")


def test_lista_nie_robi_n_plus_1(client: Client, make_download: Callable[..., Download]) -> None:
    """Liczba zapytań ma być stała niezależnie od liczby plików na stronie."""
    for index in range(2):
        make_download(
            order=index, pl={"title": f"A{index}", "status": PublicationStatus.PUBLISHED}
        )
    with CaptureQueriesContext(connection) as small:
        client.get("/api/v1/pl/downloads/")

    cache.clear()
    for index in range(5):
        make_download(
            order=index + 10, pl={"title": f"B{index}", "status": PublicationStatus.PUBLISHED}
        )
    with CaptureQueriesContext(connection) as large:
        client.get("/api/v1/pl/downloads/")

    assert len(large) == len(small), (
        f"liczba zapytań rośnie z liczbą plików: {len(small)} -> {len(large)}"
    )


def test_domyslny_limit_to_60_na_minute() -> None:
    from downloads.throttling import DownloadsAnonRateThrottle

    throttle = DownloadsAnonRateThrottle()
    assert throttle.get_rate() == "60/min"
