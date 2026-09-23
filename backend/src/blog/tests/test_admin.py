"""Lista w panelu: brakujące i nieopublikowane tłumaczenia muszą być widoczne."""

from collections.abc import Callable
from typing import Any

import pytest
from django.contrib.admin.sites import AdminSite
from django.test import RequestFactory

from blog.admin import PostAdmin, TranslationCompletenessFilter
from blog.constants import Language, PostStatus
from blog.models import Post, PostTranslation

pytestmark = pytest.mark.django_db


@pytest.fixture
def post_admin() -> PostAdmin:
    return PostAdmin(Post, AdminSite())


def apply_filter(post_admin: PostAdmin, value: str) -> list[Post]:
    request = RequestFactory().get("/", {TranslationCompletenessFilter.parameter_name: value})
    list_filter = TranslationCompletenessFilter(
        request,
        # Django ≥ 5.0 podaje filtrom wartości parametrów jako listy.
        {TranslationCompletenessFilter.parameter_name: [value]},
        Post,
        post_admin,
    )
    queryset = list_filter.queryset(request, Post.objects.all())
    return list(queryset if queryset is not None else Post.objects.all())


def test_kolumna_pokazuje_brak_wersji(
    post_admin: PostAdmin, make_post: Callable[..., Post]
) -> None:
    post = make_post(pl={}, en=None)

    assert "brak wersji" in post_admin.status_en(post)
    assert "Szkic" in post_admin.status_pl(post)


def test_kolumna_pokazuje_status_per_jezyk(
    post_admin: PostAdmin, make_post: Callable[..., Post]
) -> None:
    post = make_post(
        pl={"status": PostStatus.PUBLISHED},
        en={"status": PostStatus.DRAFT},
    )

    assert "Opublikowany" in post_admin.status_pl(post)
    assert "Szkic" in post_admin.status_en(post)


def test_filtr_brak_wersji_en(post_admin: PostAdmin, make_post: Callable[..., Post]) -> None:
    bez_en = make_post(pl={}, en=None)
    make_post(pl={}, en={})

    assert apply_filter(post_admin, f"missing_{Language.EN}") == [bez_en]


def test_filtr_wersja_en_nieopublikowana(
    post_admin: PostAdmin, make_post: Callable[..., Post]
) -> None:
    szkic_en = make_post(pl={}, en={"status": PostStatus.DRAFT})
    make_post(pl={}, en={"status": PostStatus.PUBLISHED})
    make_post(pl={}, en=None)  # brak wersji to inny problem niż szkic

    assert apply_filter(post_admin, f"unpublished_{Language.EN}") == [szkic_en]


@pytest.mark.parametrize("value", ["missing_de", "cokolwiek", "", "unpublished_"])
def test_podrobiona_wartosc_filtra_nie_zawezaja_listy(
    post_admin: PostAdmin, make_post: Callable[..., Post], value: str
) -> None:
    """Wartość filtra przychodzi z query stringa, więc może być dowolna.

    Oczekiwane zachowanie przy śmieciu: pokaż wszystko, nie wywal się i nie
    udawaj, że filtr zadziałał.
    """
    post = make_post(pl={})

    assert apply_filter(post_admin, value) == [post]


def test_wyszukiwanie_po_fragmencie_nazwy_autora_zweza_liste(
    client: Any, author: Any, make_post: Callable[..., Post], settings: Any, django_user_model: Any
) -> None:
    """`PostAdmin.search_fields` dostał `"author__username"`
    (`docs/tasks/15-motyw-panelu-admina.md`) — test na faktyczne zawężenie
    wyniku wyszukiwania, nie tylko na obecność wpisu w konfiguracji: post
    innego autora, którego nazwa użytkownika nie zawiera szukanego
    fragmentu, nie może się pojawić w wyniku."""
    author.is_staff = True
    author.is_superuser = True
    author.save()
    client.force_login(author)
    post_od_autora = make_post(pl={"title": "Nalewka z pigwy"})

    inny_autor = django_user_model.objects.create_user(
        username="maria-nowak", password="haslo-testowe-123", is_staff=True
    )
    post_innego_autora = Post.objects.create(author=inny_autor)
    PostTranslation.objects.create(
        master=post_innego_autora,
        language_code="pl",
        title="Inny post",
        excerpt="Zajawka innego posta",
        content="<p>Treść</p>",
        status=PostStatus.DRAFT,
    )

    # Fragment z konfiguracji fixture `author` (`blog/tests/conftest.py`:
    # `username="redaktorka"`) — musi nie być podciągiem `"maria-nowak"`,
    # inaczej test fałszywie przeszedłby przez zbieg okoliczności w nazwach,
    # nie przez samo `author__username`.
    fragment = "aktork"
    assert fragment in author.username
    assert fragment not in inny_autor.username

    response = client.get(f"/{settings.ADMIN_URL}blog/post/", {"q": fragment})

    assert response.status_code == 200
    content = response.content.decode()
    # Kontrola pozytywna (post autora, którego szukamy, jest na liście) i
    # negatywna (post innego autora nie jest) w jednym teście — bez
    # pozytywnej połowy `not in` przeszedłby fałszywie, gdyby wyszukiwanie
    # było całkowicie zepsute (np. zawsze zwracało pustą listę).
    assert "Nalewka z pigwy" in content
    assert "Inny post" not in content
    assert post_od_autora.pk is not None


def test_zmiana_posta_otwiera_sie(
    client: Any, author: Any, make_post: Callable[..., Post], settings: Any
) -> None:
    """Dymny test panelu: formularz z edytorem i zakładkami językowymi renderuje się."""
    author.is_staff = True
    author.is_superuser = True
    author.save()
    client.force_login(author)
    post = make_post(pl={"title": "Nalewka z pigwy"})

    response = client.get(f"/{settings.ADMIN_URL}blog/post/{post.pk}/change/")

    assert response.status_code == 200
    content = response.content.decode()
    assert "Nalewka z pigwy" in content
    assert "django-prose-editor" in content  # edytor WYSIWYG, nie goły textarea
    assert "Tytuł SEO" in content


def test_lista_postow_otwiera_sie(
    client: Any, author: Any, make_post: Callable[..., Post], settings: Any
) -> None:
    author.is_staff = True
    author.is_superuser = True
    author.save()
    client.force_login(author)
    make_post(pl={"title": "Nalewka z pigwy"}, en=None)

    response = client.get(f"/{settings.ADMIN_URL}blog/post/")

    assert response.status_code == 200
    content = response.content.decode()
    assert "brak wersji" in content
    assert "Kompletność tłumaczeń" in content


def test_dodanie_posta_bez_wybrania_autora_ustawia_zalogowanego_uzytkownika(
    client: Any, author: Any, settings: Any
) -> None:
    """Dokumentuje defekt zgłoszony w review (`qa-agent`, branch `7-dodanie-postu`).

    `PostAdmin.save_model` (`blog/admin.py:159-163`) zakłada domyślnego
    autora, gdy pole jest puste — ale `Post.author` (`blog/models.py:87-95`)
    nie ma `blank=True`, więc `PostAdminForm` wymaga wyboru autora na
    formularzu *zanim* `save_model` w ogóle się wykona. W praktyce redaktor
    (jedna, nietechniczna osoba — `.claude/rules/content-admin.md`) musi za
    każdym razem ręcznie wybrać siebie z listy — funkcja auto-uzupełnienia
    jest martwym kodem.

    Test na razie FAILS: to jest oczekiwane, udokumentowane zachowanie
    (czerwony test opisujący kryterium akceptacji), nie regresja
    wprowadzona przez `qa-agent`. Naprawa u `backend-agent`: albo ukryć pole
    `author` i zawsze podstawiać `request.user` (dopisując wyjątek dla
    superusera, jeśli ma zmieniać autora), albo dodać `initial` na polu
    formularza, żeby redaktor nie musiał wybierać ręcznie.
    """
    author.is_staff = True
    author.is_superuser = True
    author.save()
    client.force_login(author)

    data = {
        "title": "Post bez wybranego autora",
        "slug": "",
        "excerpt": "Zajawka testowa do sprawdzenia domyślnego autora.",
        "content": "<p>Treść</p>",
        "cover_image_alt": "",
        "meta_title": "",
        "meta_description": "",
        "status": "draft",
        "published_at": "",
        "_save": "Zapisz",
    }

    response = client.post(f"/{settings.ADMIN_URL}blog/post/add/?language=pl", data)

    assert response.status_code == 302, (
        "Oczekiwano przekierowania po udanym zapisie (autor uzupełniony "
        f"automatycznie), a dostano 200 — formularz zgłosił błąd walidacji: "
        f"{response.content.decode()[:500]!r}"
    )
    created = Post.objects.get()
    assert created.author_id == author.pk
