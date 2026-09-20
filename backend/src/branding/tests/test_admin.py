"""Panel redakcyjny: singleton — brak drugiego rekordu, redirect z listy.

Wzorowane 1:1 na `about.tests.test_admin` (`docs/tasks/11-branding-header.md`).
"""

from collections.abc import Callable
from typing import Any

import pytest
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import Permission
from django.test import RequestFactory

from branding.admin import SiteBrandingAdmin
from branding.models import SiteBranding, SocialLink, SocialPlatform

pytestmark = pytest.mark.django_db


@pytest.fixture
def branding_admin() -> SiteBrandingAdmin:
    return SiteBrandingAdmin(SiteBranding, AdminSite())


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
    branding_admin: SiteBrandingAdmin, superuser_request: Any
) -> None:
    assert branding_admin.has_add_permission(superuser_request) is True


def test_dodanie_zablokowane_gdy_singleton_juz_istnieje(
    branding_admin: SiteBrandingAdmin,
    superuser_request: Any,
    make_branding: Callable[..., SiteBranding],
) -> None:
    make_branding()

    assert branding_admin.has_add_permission(superuser_request) is False


def test_lista_przekierowuje_do_edycji_gdy_singleton_istnieje(
    client: Any, django_user_model: Any, settings: Any, make_branding: Callable[..., SiteBranding]
) -> None:
    user = django_user_model.objects.create_user(
        username="redaktorka", password="haslo-testowe-123", is_staff=True, is_superuser=True
    )
    client.force_login(user)
    branding = make_branding()

    response = client.get(f"/{settings.ADMIN_URL}branding/sitebranding/")

    assert response.status_code == 302
    assert response.url == f"/{settings.ADMIN_URL}branding/sitebranding/{branding.pk}/change/"


def test_lista_przekierowuje_do_dodania_gdy_brak_singletona(
    client: Any, django_user_model: Any, settings: Any
) -> None:
    user = django_user_model.objects.create_user(
        username="redaktorka", password="haslo-testowe-123", is_staff=True, is_superuser=True
    )
    client.force_login(user)

    response = client.get(f"/{settings.ADMIN_URL}branding/sitebranding/")

    assert response.status_code == 302
    assert response.url == f"/{settings.ADMIN_URL}branding/sitebranding/add/"


def test_bezposrednie_wejscie_na_add_jest_zablokowane_gdy_singleton_istnieje(
    client: Any, django_user_model: Any, settings: Any, make_branding: Callable[..., SiteBranding]
) -> None:
    """`has_add_permission` musi blokować `add/` niezależnie od `changelist_view` —
    redaktor mógłby wpisać adres ręcznie, z pominięciem listy."""
    user = django_user_model.objects.create_user(
        username="redaktorka", password="haslo-testowe-123", is_staff=True, is_superuser=True
    )
    client.force_login(user)
    make_branding()

    response = client.get(f"/{settings.ADMIN_URL}branding/sitebranding/add/")

    assert response.status_code == 403


def test_changelist_zwraca_403_dla_staff_bez_uprawnien_do_sitebranding(
    client: Any, django_user_model: Any, settings: Any, make_branding: Callable[..., SiteBranding]
) -> None:
    """Analogicznie do `about.tests.test_admin`
    (`test_changelist_zwraca_403_dla_staff_bez_uprawnien_do_aboutme`) —
    zamiast przekierowania ujawniającego PK singletona, staff bez uprawnień
    dostaje standardowe `403` Django."""
    staff_without_permissions = django_user_model.objects.create_user(
        username="redaktor-bez-uprawnien", password="haslo-testowe-123", is_staff=True
    )
    client.force_login(staff_without_permissions)
    make_branding()

    response = client.get(f"/{settings.ADMIN_URL}branding/sitebranding/")

    assert response.status_code == 403


def test_changelist_nadal_przekierowuje_do_edycji_dla_uprawnionego_konta(
    client: Any, django_user_model: Any, settings: Any, make_branding: Callable[..., SiteBranding]
) -> None:
    staff_with_permissions = django_user_model.objects.create_user(
        username="redaktorka-z-uprawnieniami", password="haslo-testowe-123", is_staff=True
    )
    staff_with_permissions.user_permissions.add(
        *Permission.objects.filter(
            content_type__app_label="branding",
            codename__in=["view_sitebranding", "change_sitebranding"],
        )
    )
    client.force_login(staff_with_permissions)
    branding = make_branding()

    response = client.get(f"/{settings.ADMIN_URL}branding/sitebranding/")

    assert response.status_code == 302
    assert response.url == f"/{settings.ADMIN_URL}branding/sitebranding/{branding.pk}/change/"


def test_formularz_edycji_renderuje_sie_z_inline_linkow_social_media(
    client: Any, django_user_model: Any, settings: Any, make_branding: Callable[..., SiteBranding]
) -> None:
    user = django_user_model.objects.create_user(
        username="redaktorka", password="haslo-testowe-123", is_staff=True, is_superuser=True
    )
    client.force_login(user)
    branding = make_branding()

    response = client.get(f"/{settings.ADMIN_URL}branding/sitebranding/{branding.pk}/change/")

    assert response.status_code == 200
    content = response.content.decode()
    assert "Linki social media" in content  # inline linków social media jest obecny


def test_formularz_edycji_renderuje_ikonke_platformy_dla_istniejacego_linku(
    client: Any,
    django_user_model: Any,
    settings: Any,
    make_branding: Callable[..., SiteBranding],
    make_social_link: Callable[..., SocialLink],
) -> None:
    """`SocialLinkInline.platform_icon` (`branding/admin.py`) ma pokazywać
    ikonkę SVG platformy obok dropdowna, nie tylko sam tekst z `choices`
    (`.claude/rules/content-admin.md`: panel dla osoby nietechnicznej)."""
    user = django_user_model.objects.create_user(
        username="redaktorka", password="haslo-testowe-123", is_staff=True, is_superuser=True
    )
    client.force_login(user)
    branding = make_branding()
    make_social_link(branding, platform=SocialPlatform.LINKEDIN)

    response = client.get(f"/{settings.ADMIN_URL}branding/sitebranding/{branding.pk}/change/")

    assert response.status_code == 200
    assert b"<svg" in response.content


def test_post_z_zaznaczonym_delete_usuwa_social_link(
    client: Any,
    django_user_model: Any,
    settings: Any,
    make_branding: Callable[..., SiteBranding],
    make_social_link: Callable[..., SocialLink],
) -> None:
    """`SocialLinkInline` jest standardowym `TabularInline` z `can_delete`
    włączonym domyślnie (`branding/admin.py`), ale samo GET-owe sprawdzenie
    obecności inline'a (`test_formularz_edycji_renderuje_sie_z_inline_linkow_social_media`)
    nie dowodzi, że checkbox „Usuń" faktycznie coś usuwa po stronie serwera —
    wzorzec POST z formsetem jak w
    `about.tests.test_admin_form.test_admin_odrzuca_podmieniona_zawartosc_zdjecia_certyfikatu_przez_http`,
    tu z happy-pathem `DELETE`."""
    user = django_user_model.objects.create_user(
        username="redaktorka", password="haslo-testowe-123", is_staff=True, is_superuser=True
    )
    client.force_login(user)
    branding = make_branding()
    link_to_delete = make_social_link(
        branding,
        platform=SocialPlatform.LINKEDIN,
        url="https://www.linkedin.com/in/example",
        order=0,
    )
    remaining_link = make_social_link(
        branding,
        platform=SocialPlatform.INSTAGRAM,
        url="https://www.instagram.com/example",
        order=1,
    )

    data = {
        "social_links-TOTAL_FORMS": "2",
        "social_links-INITIAL_FORMS": "2",
        "social_links-MIN_NUM_FORMS": "0",
        "social_links-MAX_NUM_FORMS": "1000",
        "social_links-0-id": str(link_to_delete.pk),
        "social_links-0-branding": str(branding.pk),
        "social_links-0-platform": SocialPlatform.LINKEDIN,
        "social_links-0-url": "https://www.linkedin.com/in/example",
        "social_links-0-order": "0",
        "social_links-0-DELETE": "1",
        "social_links-1-id": str(remaining_link.pk),
        "social_links-1-branding": str(branding.pk),
        "social_links-1-platform": SocialPlatform.INSTAGRAM,
        "social_links-1-url": "https://www.instagram.com/example",
        "social_links-1-order": "1",
        "_save": "Zapisz",
    }

    response = client.post(
        f"/{settings.ADMIN_URL}branding/sitebranding/{branding.pk}/change/", data=data
    )

    assert response.status_code == 302, (
        "Oczekiwano przekierowania po udanym zapisie formseta z zaznaczonym "
        f"DELETE, a dostano 200 — formularz zgłosił błąd walidacji: "
        f"{response.content.decode()[:500]!r}"
    )
    assert not SocialLink.objects.filter(pk=link_to_delete.pk).exists()
    assert SocialLink.objects.filter(pk=remaining_link.pk).exists()
