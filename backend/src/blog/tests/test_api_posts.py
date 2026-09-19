"""Publiczne, read-only API bloga (`/api/v1/{lang}/posts/...`).

Przypadki brzegowe wymienione wprost w `.claude/rules/conventions.md` i w
`docs/tasks/8-publiczne-api.md`. Widoczność (draft/archived, brak
tłumaczenia, slug z innego języka) jest już przetestowana na poziomie
querysetu w `test_querysets.py` — tutaj sprawdzamy, że API **korzysta**
z tych granic i poprawnie tłumaczy je na kody HTTP/kształt odpowiedzi,
nie duplikujemy tamtych testów.
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

from blog.constants import PostStatus
from blog.models import Post

pytestmark = pytest.mark.django_db


def _valid_jpeg() -> SimpleUploadedFile:
    buffer = BytesIO()
    Image.new("RGB", (2, 2), color="red").save(buffer, format="JPEG")
    return SimpleUploadedFile("okladka.jpg", buffer.getvalue(), content_type="image/jpeg")


@pytest.fixture(autouse=True)
def _clear_throttle_cache() -> Any:
    """Throttling trzyma stan w cache (Redis) — nie ma zniknąć między testami."""
    cache.clear()
    yield
    cache.clear()


# --- Lista ----------------------------------------------------------------


def test_pusta_lista_daje_200_i_pusty_wynik(client: Client) -> None:
    response = client.get("/api/v1/pl/posts/")

    assert response.status_code == 200
    assert response.json()["results"] == []


def test_lista_pokazuje_tylko_opublikowane(client: Client, make_post: Callable[..., Post]) -> None:
    make_post(pl={"title": "Szkic", "status": PostStatus.DRAFT})
    make_post(pl={"title": "Archiwum", "status": PostStatus.ARCHIVED})
    make_post(pl={"title": "Widoczny", "status": PostStatus.PUBLISHED})

    response = client.get("/api/v1/pl/posts/")

    titles = [item["title"] for item in response.json()["results"]]
    assert titles == ["Widoczny"]


def test_lista_nie_zawiera_pelnej_tresci(client: Client, make_post: Callable[..., Post]) -> None:
    make_post(pl={"status": PostStatus.PUBLISHED, "content": "<p>Sekretna treść</p>"})

    response = client.get("/api/v1/pl/posts/")

    item = response.json()["results"][0]
    assert "content" not in item
    assert set(item) == {
        "slug",
        "title",
        "excerpt",
        "cover_image",
        "cover_image_alt",
        "author",
        "published_at",
    }


def test_lista_paginuje_po_pieciu(client: Client, make_post: Callable[..., Post]) -> None:
    for index in range(7):
        make_post(pl={"title": f"Post {index}", "status": PostStatus.PUBLISHED})

    first_page = client.get("/api/v1/pl/posts/").json()
    second_page = client.get("/api/v1/pl/posts/?page=2").json()

    assert len(first_page["results"]) == 5
    assert len(second_page["results"]) == 2
    assert first_page["count"] == 7


def test_lista_bez_okladki_daje_null(client: Client, make_post: Callable[..., Post]) -> None:
    make_post(pl={"status": PostStatus.PUBLISHED})

    item = client.get("/api/v1/pl/posts/").json()["results"][0]

    assert item["cover_image"] is None


@override_settings(SITE_URL="https://okowformie.pl")
def test_okladka_uzywa_site_url_a_nie_hosta_zadania(
    client: Client, make_post: Callable[..., Post]
) -> None:
    """Absolutny URL okładki ma pochodzić z `settings.SITE_URL`, nie z
    nagłówka `Host` żądania (test client domyślnie woła `testserver`) —
    inaczej server-side fetch z kontenera frontendu (`Host: backend:8000`)
    wyciekłby do `og:image`/JSON-LD jako nieosiągalny z zewnątrz adres
    wewnętrzny."""
    post = make_post(pl={"status": PostStatus.PUBLISHED})
    post.cover_image = _valid_jpeg()
    post.save()

    item = client.get("/api/v1/pl/posts/").json()["results"][0]

    assert item["cover_image"].startswith("https://okowformie.pl/media/")
    assert "testserver" not in item["cover_image"]


def test_zly_lang_daje_404(client: Client, make_post: Callable[..., Post]) -> None:
    make_post(pl={"status": PostStatus.PUBLISHED})

    response = client.get("/api/v1/de/posts/")

    assert response.status_code == 404


def test_lista_nie_robi_n_plus_1(client: Client, make_post: Callable[..., Post]) -> None:
    """Liczba zapytań ma być stała niezależnie od liczby postów na stronie."""
    for index in range(2):
        make_post(pl={"title": f"A{index}", "status": PostStatus.PUBLISHED})
    with CaptureQueriesContext(connection) as small:
        client.get("/api/v1/pl/posts/")

    cache.clear()
    for index in range(5):
        make_post(pl={"title": f"B{index}", "status": PostStatus.PUBLISHED})
    with CaptureQueriesContext(connection) as large:
        client.get("/api/v1/pl/posts/")

    assert len(large) == len(small), (
        f"liczba zapytań rośnie z liczbą postów: {len(small)} -> {len(large)}"
    )


# --- Szczegół ---------------------------------------------------------------


def test_szczegol_zwraca_sanityzowana_tresc(client: Client, make_post: Callable[..., Post]) -> None:
    make_post(
        pl={
            "slug": "post-z-payloadem",
            "status": PostStatus.PUBLISHED,
            "content": '<p>Ok</p><script>alert("xss")</script><img src="x" onerror="alert(1)">',
        }
    )

    response = client.get("/api/v1/pl/posts/post-z-payloadem/")

    content = response.json()["content"]
    assert "<script" not in content
    assert "onerror" not in content
    assert "<p>Ok</p>" in content


def test_szczegol_zawiera_pola_szczegolu(client: Client, make_post: Callable[..., Post]) -> None:
    make_post(
        pl={
            "slug": "pelny-post",
            "status": PostStatus.PUBLISHED,
            "meta_title": "Tytuł SEO",
            "meta_description": "Opis SEO",
        },
        en={"slug": "full-post", "status": PostStatus.PUBLISHED},
    )

    response = client.get("/api/v1/pl/posts/pelny-post/")

    body = response.json()
    assert body["meta_title"] == "Tytuł SEO"
    assert body["meta_description"] == "Opis SEO"
    assert "updated_at" in body
    assert body["available_translations"] == [
        {"language": "en", "slug": "full-post"},
        {"language": "pl", "slug": "pelny-post"},
    ]


def test_puste_pola_seo_maja_fallback_na_tytul_i_zajawke(
    client: Client, make_post: Callable[..., Post]
) -> None:
    """`.claude/rules/seo.md`: nigdy pusty tag w HTML — redaktor zostawia te

    pola puste na co dzień (`content-admin.md`), więc to jest ścieżka
    domyślna, nie brzegowa.
    """
    make_post(
        pl={
            "slug": "bez-seo",
            "title": "Tytuł bez SEO",
            "excerpt": "Zajawka bez SEO",
            "status": PostStatus.PUBLISHED,
            "meta_title": "",
            "meta_description": "",
        }
    )

    body = client.get("/api/v1/pl/posts/bez-seo/").json()

    assert body["meta_title"] == "Tytuł bez SEO"
    assert body["meta_description"] == "Zajawka bez SEO"


def test_szczegol_ukrywa_niepublikowane_tlumaczenie_z_available_translations(
    client: Client, make_post: Callable[..., Post]
) -> None:
    make_post(
        pl={"slug": "post-pl", "status": PostStatus.PUBLISHED},
        en={"slug": "post-en", "status": PostStatus.DRAFT},
    )

    body = client.get("/api/v1/pl/posts/post-pl/").json()

    assert body["available_translations"] == [{"language": "pl", "slug": "post-pl"}]


def test_nieistniejacy_slug_daje_404(client: Client) -> None:
    response = client.get("/api/v1/pl/posts/nigdy-nie-istnial/")

    assert response.status_code == 404


def test_szkic_daje_404_w_szczegole(client: Client, make_post: Callable[..., Post]) -> None:
    make_post(pl={"slug": "tajny-szkic", "status": PostStatus.DRAFT})

    response = client.get("/api/v1/pl/posts/tajny-szkic/")

    assert response.status_code == 404


def test_archiwum_daje_404_w_szczegole(client: Client, make_post: Callable[..., Post]) -> None:
    make_post(pl={"slug": "stary-post", "status": PostStatus.ARCHIVED})

    response = client.get("/api/v1/pl/posts/stary-post/")

    assert response.status_code == 404


def test_post_bez_tlumaczenia_en_daje_404_nie_polska_tresc(
    client: Client, make_post: Callable[..., Post]
) -> None:
    make_post(pl={"slug": "tylko-polski", "status": PostStatus.PUBLISHED}, en=None)

    response = client.get("/api/v1/en/posts/tylko-polski/")

    assert response.status_code == 404


def test_slug_z_jednego_jezyka_nie_dziala_w_drugim(
    client: Client, make_post: Callable[..., Post]
) -> None:
    make_post(
        pl={"slug": "nalewka-z-pigwy", "status": PostStatus.PUBLISHED},
        en={"slug": "quince-liqueur", "status": PostStatus.PUBLISHED},
    )

    response = client.get("/api/v1/en/posts/nalewka-z-pigwy/")

    assert response.status_code == 404


def test_zly_lang_daje_404_w_szczegole(client: Client, make_post: Callable[..., Post]) -> None:
    make_post(pl={"slug": "post", "status": PostStatus.PUBLISHED})

    response = client.get("/api/v1/de/posts/post/")

    assert response.status_code == 404


def test_szczegol_nie_robi_n_plus_1(client: Client, make_post: Callable[..., Post]) -> None:
    make_post(
        pl={"slug": "n-plus-1", "status": PostStatus.PUBLISHED},
        en={"slug": "n-plus-1-en", "status": PostStatus.PUBLISHED},
    )

    with CaptureQueriesContext(connection) as queries:
        response = client.get("/api/v1/pl/posts/n-plus-1/")

    assert response.status_code == 200
    assert len(queries) <= 2, f"oczekiwano <=2 zapytań, było {len(queries)}: {list(queries)}"


# --- Autor ------------------------------------------------------------------


def test_autor_pokazuje_pelne_imie_i_nazwisko(
    client: Client, make_post: Callable[..., Post], author: Any
) -> None:
    author.first_name = "Anna"
    author.last_name = "Redaktorka"
    author.save()
    make_post(pl={"status": PostStatus.PUBLISHED})

    item = client.get("/api/v1/pl/posts/").json()["results"][0]

    assert item["author"] == "Anna Redaktorka"


def test_autor_bez_danych_konta(client: Client, make_post: Callable[..., Post]) -> None:
    make_post(pl={"status": PostStatus.PUBLISHED})

    item = client.get("/api/v1/pl/posts/").json()["results"][0]

    assert item["author"] not in {"redaktorka", ""}
    assert "email" not in item
    assert "is_staff" not in item
    assert "username" not in item


# --- Cache-Control ------------------------------------------------------------


def test_lista_ma_naglowek_cache_control(client: Client, make_post: Callable[..., Post]) -> None:
    make_post(pl={"status": PostStatus.PUBLISHED})

    response = client.get("/api/v1/pl/posts/")

    assert "max-age" in response.headers.get("Cache-Control", "")


def test_szczegol_ma_naglowek_cache_control(client: Client, make_post: Callable[..., Post]) -> None:
    make_post(pl={"slug": "post-z-cache", "status": PostStatus.PUBLISHED})

    response = client.get("/api/v1/pl/posts/post-z-cache/")

    assert "max-age" in response.headers.get("Cache-Control", "")


# --- Throttling ---------------------------------------------------------------


def test_przekroczony_limit_daje_429(client: Client, make_post: Callable[..., Post]) -> None:
    """Bije w realny, skonfigurowany limit (60/min) zamiast go podmieniać.

    `SimpleRateThrottle.THROTTLE_RATES` z DRF-a jest wiązane raz, przy
    imporcie modułu (`THROTTLE_RATES = api_settings.DEFAULT_THROTTLE_RATES`
    jako atrybut klasy) — `override_settings` w trakcie testu nic tu nie
    zmienia, więc jedyny wiarygodny sposób sprawdzenia 429 to realnie
    wyczerpać limit.
    """
    make_post(pl={"status": PostStatus.PUBLISHED})

    responses = [client.get("/api/v1/pl/posts/") for _ in range(61)]

    assert [r.status_code for r in responses[:60]] == [200] * 60
    assert responses[60].status_code == 429


def test_domyslny_limit_to_60_na_minute() -> None:
    from blog.throttling import PostsAnonRateThrottle

    throttle = PostsAnonRateThrottle()
    assert throttle.get_rate() == "60/min"
