"""Niezmienniki modelu: slug, sanityzacja przy zapisie i odczycie, publikacja."""

from collections.abc import Callable
from typing import Any

import pytest
from django.db import IntegrityError
from django.utils import timezone

from blog.constants import Language, PostStatus
from blog.models import Post, PostTranslation

pytestmark = pytest.mark.django_db


# --- Slug ---------------------------------------------------------------


def test_slug_generuje_sie_z_tytulu(make_post: Callable[..., Post]) -> None:
    post = make_post(pl={"title": "Żurawina na zimę"})

    assert post.translations.get(language_code=Language.PL).slug == "zurawina-na-zime"


def test_slug_podany_recznie_zostaje_uszanowany(make_post: Callable[..., Post]) -> None:
    post = make_post(pl={"title": "Żurawina na zimę", "slug": "moj-wlasny-adres"})

    assert post.translations.get(language_code=Language.PL).slug == "moj-wlasny-adres"


def test_ten_sam_slug_moze_istniec_w_obu_jezykach(make_post: Callable[..., Post]) -> None:
    """Unikalność jest w obrębie języka, nie globalnie."""
    post = make_post(
        pl={"title": "Gin", "slug": "gin"},
        en={"title": "Gin", "slug": "gin"},
    )

    slugs = {t.language_code: t.slug for t in post.translations.all()}
    assert slugs == {Language.PL: "gin", Language.EN: "gin"}


def test_kolizja_slugow_w_jednym_jezyku_dostaje_sufiks(make_post: Callable[..., Post]) -> None:
    make_post(pl={"title": "Gin"})
    second = make_post(pl={"title": "Gin"})

    assert second.translations.get(language_code=Language.PL).slug == "gin-2"


def test_baza_nie_przepusci_duplikatu_slugu_w_jednym_jezyku(
    make_post: Callable[..., Post], author: Any
) -> None:
    make_post(pl={"title": "Gin", "slug": "gin"})
    other = Post.objects.create(author=author)

    with pytest.raises(IntegrityError):
        # Z pominięciem `save()` modelu, żeby sprawdzić samo ograniczenie bazy.
        PostTranslation.objects.bulk_create(
            [
                PostTranslation(
                    master=other,
                    language_code=Language.PL,
                    title="Gin",
                    slug="gin",
                    excerpt="x",
                )
            ]
        )


# --- Sanityzacja --------------------------------------------------------


def test_zapis_czysci_tresc(make_post: Callable[..., Post]) -> None:
    post = make_post(pl={"content": '<p>Ok</p><script>alert("xss")</script>'})

    stored = post.translations.get(language_code=Language.PL).content
    assert "<script" not in stored
    assert "<p>Ok</p>" in stored


def test_odczyt_czysci_tresc_wpisana_z_pominieciem_save(make_post: Callable[..., Post]) -> None:
    """Druga warstwa obrony: wiersz wstawiony bez `save()` też nie wycieka."""
    post = make_post(pl={})
    PostTranslation.objects.filter(master=post, language_code=Language.PL).update(
        content='<img src="x" onerror="alert(1)">'
    )

    translation = PostTranslation.objects.get(master=post, language_code=Language.PL)

    assert "onerror" in translation.content  # surowa kolumna faktycznie skażona
    assert "onerror" not in translation.content_html


# --- Publikacja ---------------------------------------------------------


def test_publikacja_stempluje_date(make_post: Callable[..., Post]) -> None:
    before = timezone.now()
    post = make_post(pl={"status": PostStatus.PUBLISHED})

    published_at = post.translations.get(language_code=Language.PL).published_at
    assert published_at is not None
    assert published_at >= before


def test_szkic_nie_ma_daty_publikacji(make_post: Callable[..., Post]) -> None:
    post = make_post(pl={"status": PostStatus.DRAFT})

    assert post.translations.get(language_code=Language.PL).published_at is None


def test_archiwizacja_nie_kasuje_daty_publikacji(make_post: Callable[..., Post]) -> None:
    post = make_post(pl={"status": PostStatus.PUBLISHED})
    translation = post.translations.get(language_code=Language.PL)
    original = translation.published_at

    translation.status = PostStatus.ARCHIVED
    translation.save()

    translation.refresh_from_db()
    assert translation.published_at == original


def test_status_jest_niezalezny_miedzy_jezykami(make_post: Callable[..., Post]) -> None:
    post = make_post(
        pl={"status": PostStatus.PUBLISHED},
        en={"status": PostStatus.DRAFT},
    )

    statuses = {t.language_code: t.status for t in post.translations.all()}
    assert statuses == {Language.PL: PostStatus.PUBLISHED, Language.EN: PostStatus.DRAFT}


# --- Fallbacki SEO ------------------------------------------------------


def test_seo_wpada_na_tytul_i_zajawke_gdy_pola_puste(make_post: Callable[..., Post]) -> None:
    post = make_post(pl={"title": "Tytuł posta", "excerpt": "Zajawka posta"})

    translation = post.translations.get(language_code=Language.PL)
    assert translation.seo_title == "Tytuł posta"
    assert translation.seo_description == "Zajawka posta"


def test_seo_uzywa_nadpisan_gdy_sa(make_post: Callable[..., Post]) -> None:
    post = make_post(pl={"meta_title": "Inny tytuł", "meta_description": "Inny opis"})

    translation = post.translations.get(language_code=Language.PL)
    assert translation.seo_title == "Inny tytuł"
    assert translation.seo_description == "Inny opis"
