"""Panel redakcyjny: singleton — brak drugiego rekordu, redirect z listy."""

from collections.abc import Callable
from typing import Any

import pytest
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import Permission
from django.test import RequestFactory

from about.admin import AboutMeAdmin
from about.models import AboutMe

pytestmark = pytest.mark.django_db


@pytest.fixture
def about_admin() -> AboutMeAdmin:
    return AboutMeAdmin(AboutMe, AdminSite())


@pytest.fixture
def superuser_request(django_user_model: Any) -> Any:
    """`has_add_permission` sięga po `request.user.has_perm(...)` — `RequestFactory`
    sam z siebie nie dokłada `user` (to robi `AuthenticationMiddleware`)."""
    user = django_user_model.objects.create_superuser(
        username="redaktorka", password="haslo-testowe-123"
    )
    request = RequestFactory().get("/")
    request.user = user
    return request


def test_dodanie_dozwolone_gdy_singleton_nie_istnieje(
    about_admin: AboutMeAdmin, superuser_request: Any
) -> None:
    assert about_admin.has_add_permission(superuser_request) is True


def test_dodanie_zablokowane_gdy_singleton_juz_istnieje(
    about_admin: AboutMeAdmin, superuser_request: Any, make_about: Callable[..., AboutMe]
) -> None:
    make_about(pl={})

    assert about_admin.has_add_permission(superuser_request) is False


def test_lista_przekierowuje_do_edycji_gdy_singleton_istnieje(
    client: Any, django_user_model: Any, settings: Any, make_about: Callable[..., AboutMe]
) -> None:
    user = django_user_model.objects.create_user(
        username="redaktorka", password="haslo-testowe-123", is_staff=True, is_superuser=True
    )
    client.force_login(user)
    about = make_about(pl={"headline": "Optometrysta"})

    response = client.get(f"/{settings.ADMIN_URL}about/aboutme/")

    assert response.status_code == 302
    assert response.url == f"/{settings.ADMIN_URL}about/aboutme/{about.pk}/change/"


def test_lista_przekierowuje_do_dodania_gdy_brak_singletona(
    client: Any, django_user_model: Any, settings: Any
) -> None:
    user = django_user_model.objects.create_user(
        username="redaktorka", password="haslo-testowe-123", is_staff=True, is_superuser=True
    )
    client.force_login(user)

    response = client.get(f"/{settings.ADMIN_URL}about/aboutme/")

    assert response.status_code == 302
    assert response.url == f"/{settings.ADMIN_URL}about/aboutme/add/"


def test_bezposrednie_wejscie_na_add_jest_zablokowane_gdy_singleton_istnieje(
    client: Any, django_user_model: Any, settings: Any, make_about: Callable[..., AboutMe]
) -> None:
    """`has_add_permission` musi blokować `add/` niezależnie od `changelist_view` —
    redaktor mógłby wpisać adres ręcznie, z pominięciem listy."""
    user = django_user_model.objects.create_user(
        username="redaktorka", password="haslo-testowe-123", is_staff=True, is_superuser=True
    )
    client.force_login(user)
    make_about(pl={})

    response = client.get(f"/{settings.ADMIN_URL}about/aboutme/add/")

    assert response.status_code == 403


def test_changelist_zwraca_403_dla_staff_bez_uprawnien_do_aboutme(
    client: Any, django_user_model: Any, settings: Any, make_about: Callable[..., AboutMe]
) -> None:
    """`changelist_view` (`about/admin.py`) sprawdza `has_view_or_change_permission`
    **przed** policzeniem przekierowania, więc staff bez żadnych uprawnień do
    `AboutMe` (scenariusz z `.claude/rules/scope.md`: konta redakcyjne mogą
    mieć różne role, nie każdy staff to superuser) dostaje standardowe `403`
    Django — dokładnie to, co dostałby `Post`-owy changelist w tej samej
    sytuacji — zamiast przekierowania ujawniającego PK singletona (wyciek
    metadanych: potwierdzenie istnienia rekordu i jego identyfikator)."""
    staff_without_permissions = django_user_model.objects.create_user(
        username="redaktor-bez-uprawnien", password="haslo-testowe-123", is_staff=True
    )
    client.force_login(staff_without_permissions)
    make_about(pl={})

    response = client.get(f"/{settings.ADMIN_URL}about/aboutme/")

    assert response.status_code == 403


def test_changelist_nadal_przekierowuje_do_edycji_dla_uprawnionego_konta(
    client: Any, django_user_model: Any, settings: Any, make_about: Callable[..., AboutMe]
) -> None:
    """Sprawdzenie uprawnień w `changelist_view` nie może zmienić dotychczasowego
    zachowania dla konta, które faktycznie ma uprawnienia do `AboutMe` — dalej
    dostaje redirect wprost do edycji singletona (patrz też
    `test_lista_przekierowuje_do_edycji_gdy_singleton_istnieje`, wariant przez
    superusera; tu przez zwykłego staff z jawnie nadanymi uprawnieniami)."""
    staff_with_permissions = django_user_model.objects.create_user(
        username="redaktorka-z-uprawnieniami", password="haslo-testowe-123", is_staff=True
    )
    staff_with_permissions.user_permissions.add(
        *Permission.objects.filter(
            content_type__app_label="about",
            codename__in=["view_aboutme", "change_aboutme"],
        )
    )
    client.force_login(staff_with_permissions)
    about = make_about(pl={})

    response = client.get(f"/{settings.ADMIN_URL}about/aboutme/")

    assert response.status_code == 302
    assert response.url == f"/{settings.ADMIN_URL}about/aboutme/{about.pk}/change/"


def test_formularz_edycji_renderuje_sie_z_edytorem_i_inline_certyfikatow(
    client: Any, django_user_model: Any, settings: Any, make_about: Callable[..., AboutMe]
) -> None:
    user = django_user_model.objects.create_user(
        username="redaktorka", password="haslo-testowe-123", is_staff=True, is_superuser=True
    )
    client.force_login(user)
    about = make_about(pl={"headline": "Optometrysta"})

    response = client.get(f"/{settings.ADMIN_URL}about/aboutme/{about.pk}/change/")

    assert response.status_code == 200
    content = response.content.decode()
    assert "Optometrysta" in content
    assert "django-prose-editor" in content  # edytor WYSIWYG, nie goły textarea
    assert "Certyfikaty" in content  # inline certyfikatów jest obecny
