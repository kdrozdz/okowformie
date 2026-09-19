"""Widoczność publiczna: co wolno zwrócić, a co musi zniknąć.

To są przypadki brzegowe wymienione wprost w `.claude/rules/conventions.md`.
Testujemy je na poziomie querysetu, bo tam — i tylko tam — wolno filtrować
po statusie (`.claude/rules/security.md`).
"""

from collections.abc import Callable

import pytest
from django.db import connection

from blog.constants import Language, PostStatus
from blog.models import Post

pytestmark = pytest.mark.django_db


def test_szkic_nie_jest_widoczny_publicznie(make_post: Callable[..., Post]) -> None:
    make_post(pl={"status": PostStatus.DRAFT})

    assert Post.objects.published(Language.PL).count() == 0


def test_archiwum_nie_jest_widoczne_publicznie(make_post: Callable[..., Post]) -> None:
    make_post(pl={"status": PostStatus.ARCHIVED})

    assert Post.objects.published(Language.PL).count() == 0


def test_opublikowany_post_jest_widoczny(make_post: Callable[..., Post]) -> None:
    post = make_post(pl={"status": PostStatus.PUBLISHED})

    assert list(Post.objects.published(Language.PL)) == [post]


def test_post_bez_tlumaczenia_en_nie_wychodzi_na_liscie_en(
    make_post: Callable[..., Post],
) -> None:
    make_post(pl={"status": PostStatus.PUBLISHED}, en=None)

    assert Post.objects.published(Language.PL).count() == 1
    assert Post.objects.published(Language.EN).count() == 0


def test_post_z_en_w_szkicu_nie_wychodzi_na_liscie_en(make_post: Callable[..., Post]) -> None:
    make_post(
        pl={"status": PostStatus.PUBLISHED},
        en={"status": PostStatus.DRAFT},
    )

    assert Post.objects.published(Language.PL).count() == 1
    assert Post.objects.published(Language.EN).count() == 0


def test_slug_z_jednego_jezyka_nie_dziala_w_routingu_drugiego(
    make_post: Callable[..., Post],
) -> None:
    """Regresja na klasyczny błąd wielowartościowej relacji.

    Post ma opublikowane PL (`nalewka-z-pigwy`) i opublikowane EN
    (`quince-liqueur`). Żądanie `/en/nalewka-z-pigwy` nie może trafić w ten
    post tylko dlatego, że *jakieś* jego tłumaczenie jest opublikowane i
    *jakieś* ma ten slug.
    """
    make_post(
        pl={"slug": "nalewka-z-pigwy", "status": PostStatus.PUBLISHED},
        en={"slug": "quince-liqueur", "status": PostStatus.PUBLISHED},
    )

    with pytest.raises(Post.DoesNotExist):
        Post.objects.get_published(Language.EN, "nalewka-z-pigwy")

    assert Post.objects.get_published(Language.PL, "nalewka-z-pigwy") is not None
    assert Post.objects.get_published(Language.EN, "quince-liqueur") is not None


def test_slug_szkicu_nie_otwiera_posta(make_post: Callable[..., Post]) -> None:
    make_post(pl={"slug": "tajny-szkic", "status": PostStatus.DRAFT})

    with pytest.raises(Post.DoesNotExist):
        Post.objects.get_published(Language.PL, "tajny-szkic")


def test_slug_ktory_nigdy_nie_istnial_daje_404(make_post: Callable[..., Post]) -> None:
    """Nieistniejący slug — nie mylić z „istnieje, ale nieopublikowany"."""
    make_post(pl={"slug": "istniejacy-post", "status": PostStatus.PUBLISHED})

    with pytest.raises(Post.DoesNotExist):
        Post.objects.get_published(Language.PL, "taki-slug-nigdy-nie-istnial")


def test_pusta_lista_gdy_nie_ma_postow() -> None:
    assert list(Post.objects.published(Language.PL)) == []


def test_lista_nie_robi_n_plus_1(make_post: Callable[..., Post]) -> None:
    """Autor i tłumaczenia mają wejść razem z listą, nie po jednym zapytaniu na post."""
    for index in range(5):
        make_post(
            pl={"title": f"Post {index}", "status": PostStatus.PUBLISHED},
            en={"title": f"Post {index} EN", "status": PostStatus.PUBLISHED},
        )

    counter = _QueryCounter()
    with connection.execute_wrapper(counter):
        for post in Post.objects.published(Language.PL):
            _ = post.author.username
            _ = post.translations_by_language()

    # 1 × posty (z JOIN-em na autora) + 1 × prefetch tłumaczeń.
    assert counter.count == 2, f"oczekiwano 2 zapytań, było {counter.count}"


class _QueryCounter:
    def __init__(self) -> None:
        self.count = 0

    def __call__(self, execute, sql, params, many, context):  # type: ignore[no-untyped-def]
        self.count += 1
        return execute(sql, params, many, context)
