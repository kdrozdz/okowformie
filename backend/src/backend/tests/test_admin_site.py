"""Branding i grupowanie strony głównej panelu (`backend/admin.py`).

Testy białoskrzynkowe na już-załadowanym singletonie `admin.site`
(przypisanym na `OkowformieAdminSite` przy imporcie `backend.admin` —
`backend/urls.py`, `django.contrib.admin.apps.AdminConfig.ready()`
przez autodiscover) — nie tworzymy nowej instancji `AdminSite`, bo cały
rejestr modeli (`@admin.register` w każdej domenowej apce) żyje na tym
jednym, globalnym obiekcie (`docs/tasks/15-motyw-panelu-admina.md`).
"""

from typing import Any

import pytest
from django.contrib import admin
from django.contrib.auth.models import Permission
from django.test import RequestFactory

pytestmark = pytest.mark.django_db


def _grouped(request: Any) -> dict[str, set[tuple[str, str]]]:
    """Nazwa kategorii -> zbiór (app_label, model_name) modeli w niej.

    Zbiór, nie lista: kolejność modeli *wewnątrz* kategorii to szczegół
    implementacyjny Django (sortowanie po `verbose_name_plural`,
    `AdminSite._build_app_dict`), nie coś, co kryteria akceptacji tego
    taska precyzują — precyzują tylko kolejność *kategorii*.
    """
    return {
        app["name"]: {
            (model["model"]._meta.app_label, model["model"]._meta.model_name)
            for model in app["models"]
        }
        for app in admin.site.get_app_list(request)
    }


@pytest.fixture
def superuser_request(django_user_model: Any) -> Any:
    user = django_user_model.objects.create_superuser(
        username="redaktorka-superuser", password="haslo-testowe-123"
    )
    request = RequestFactory().get("/")
    request.user = user
    return request


# --- Grupowanie strony głównej: superuser widzi wszystko -------------------


def test_superuser_widzi_kategorie_w_oczekiwanej_kolejnosci(superuser_request: Any) -> None:
    app_list = admin.site.get_app_list(superuser_request)

    assert [app["name"] for app in app_list] == [
        "Treść",
        "Branding",
        "Konfiguracja AI",
        "Konta",
    ]


def test_superuser_widzi_kazdy_model_we_wlasciwej_kategorii(superuser_request: Any) -> None:
    grouped = _grouped(superuser_request)

    assert grouped["Treść"] == {("blog", "post"), ("about", "aboutme")}
    assert grouped["Branding"] == {("branding", "sitebranding")}
    assert grouped["Konfiguracja AI"] == {
        ("ai_content", "aiprovidersettings"),
        ("ai_content", "postgenerator"),
    }
    # `auth.Group` jest zarejestrowany w adminie domyślnie przez Django
    # (`django.contrib.auth.admin`) — regresja znaleziona przez
    # `/code-review`: bez jawnego wpisu w `_APP_LIST_CATEGORIES` znikał z
    # całej nawigacji (strona główna i sidebar), mimo że URL wciąż działał.
    assert grouped["Konta"] == {("accounts", "user"), ("auth", "group")}


def test_model_bez_kategorii_nie_znika_z_nawigacji_tylko_trafia_do_inne(
    superuser_request: Any, monkeypatch: Any
) -> None:
    """Fallback na wypadek, gdyby to samo przeoczenie (jak z `auth.Group`)
    powtórzyło się dla innego modelu w przyszłości: model zarejestrowany w
    adminie, ale nie wypisany w żadnej kategorii, trafia do kategorii
    "Inne" — nigdy nie znika bez śladu.
    """
    from backend import admin as backend_admin

    categories_without_groups = tuple(
        (slug, name, tuple(key for key in keys if key != ("auth", "group")))
        for slug, name, keys in backend_admin._APP_LIST_CATEGORIES
    )
    monkeypatch.setattr(backend_admin, "_APP_LIST_CATEGORIES", categories_without_groups)

    grouped = _grouped(superuser_request)

    assert grouped["Inne"] == {("auth", "group")}
    assert ("auth", "group") not in grouped["Konta"]


# --- Grupowanie faktycznie filtruje wg uprawnień, nie tylko układa ---------


def test_staff_z_uprawnieniami_tylko_blog_nie_widzi_brandingu_ani_kont(
    django_user_model: Any,
) -> None:
    """`AboutMe` (bez uprawnień `about.*`) i `AIProviderSettings` (bez
    uprawnień `ai_content.*`) muszą wypadać z listy tak samo jak całe
    kategorie „Branding”/„Konta” — samo `blog.add_post`+`blog.change_post`
    daje dostęp też do `PostGenerator` (`ai_content.admin.PostGeneratorAdmin.
    has_module_permission` liczy się z uprawnień `blog`, nie `ai_content` —
    istniejące zachowanie z `ai_content/admin.py`, niezmienione tym taskiem).
    """
    user = django_user_model.objects.create_user(
        username="redaktor-tylko-blog", password="haslo-testowe-123", is_staff=True
    )
    user.user_permissions.add(
        *Permission.objects.filter(
            content_type__app_label="blog", codename__in=["add_post", "change_post"]
        )
    )
    request = RequestFactory().get("/")
    request.user = user

    grouped = _grouped(request)

    assert set(grouped) == {"Treść", "Konfiguracja AI"}
    assert grouped["Treść"] == {("blog", "post")}
    assert grouped["Konfiguracja AI"] == {("ai_content", "postgenerator")}


def test_staff_z_uprawnieniami_tylko_accounts_widzi_wylacznie_konta(
    django_user_model: Any,
) -> None:
    """Odwrotny przekrój: uprawnienia tylko do `accounts.User` odsłaniają
    wyłącznie kategorię „Konta” — dowód, że filtrowanie działa niezależnie
    od tego, którą kategorię się sprawdza, nie tylko dla `blog`."""
    user = django_user_model.objects.create_user(
        username="redaktor-tylko-accounts", password="haslo-testowe-123", is_staff=True
    )
    user.user_permissions.add(
        *Permission.objects.filter(content_type__app_label="accounts", codename="view_user")
    )
    request = RequestFactory().get("/")
    request.user = user

    grouped = _grouped(request)

    assert set(grouped) == {"Konta"}
    assert grouped["Konta"] == {("accounts", "user")}


def test_staff_bez_zadnych_uprawnien_nie_widzi_zadnej_kategorii(
    django_user_model: Any,
) -> None:
    user = django_user_model.objects.create_user(
        username="redaktor-bez-uprawnien", password="haslo-testowe-123", is_staff=True
    )
    request = RequestFactory().get("/")
    request.user = user

    assert admin.site.get_app_list(request) == []


# --- Branding wizualny: logo, site_header, arkusz stylów -------------------


def test_strona_logowania_ma_branding_okowformie(client: Any, settings: Any) -> None:
    response = client.get(f"/{settings.ADMIN_URL}login/")

    assert response.status_code == 200
    content = response.content.decode()
    assert "okowFormie" in content
    assert "admin/img/logo.png" in content
    assert "okowformie-admin.css" in content


def test_strona_glowna_panelu_ma_branding_okowformie(
    client: Any, django_user_model: Any, settings: Any
) -> None:
    user = django_user_model.objects.create_superuser(
        username="redaktorka-index", password="haslo-testowe-123"
    )
    client.force_login(user)

    response = client.get(f"/{settings.ADMIN_URL}")

    assert response.status_code == 200
    content = response.content.decode()
    assert "okowFormie" in content
    assert "admin/img/logo.png" in content
    assert "okowformie-admin.css" in content
    # Sidebar nawigacji na stronie głównej korzysta z tego samego
    # `get_app_list` co strona główna — kategorie muszą tam też się pojawić
    # (`docs/tasks/15-motyw-panelu-admina.md`: efekt uboczny na cały panel).
    assert "Konfiguracja AI" in content


# --- Regresja: dark mode Django musi zostać całkowicie wyłączony -----------


def test_strona_logowania_nie_laduje_dark_mode_django(client: Any, settings: Any) -> None:
    """Zgłoszony defekt: `okowformie-admin.css` nadpisywał tylko część
    zmiennych CSS Django (np. `--body-bg`, nie `--body-fg`) — przy
    systemowym `prefers-color-scheme: dark` albo ręcznym przełączniku w
    headerze `--body-fg` zostawał jasny z `dark_mode.css`, a `--body-bg`
    jasny z naszego pliku: jasny tekst na jasnym tle ("białe kolory się
    nakładają"). Naprawa usuwa `dark_mode.css`/`theme.js`/przełącznik z
    HTML w ogóle (`admin/base_site.html`, blok `dark-mode-vars`;
    `admin/color_theme_toggle.html`), więc `data-theme` nigdy nie jest
    ustawiane i nasz jeden, jasny motyw jest jedynym możliwym stanem.
    """
    response = client.get(f"/{settings.ADMIN_URL}login/")

    content = response.content.decode()
    assert "dark_mode.css" not in content
    assert "theme.js" not in content
    assert "theme-toggle" not in content


def test_strona_glowna_panelu_nie_laduje_dark_mode_django(
    client: Any, django_user_model: Any, settings: Any
) -> None:
    user = django_user_model.objects.create_superuser(
        username="redaktorka-bez-dark-mode", password="haslo-testowe-123"
    )
    client.force_login(user)

    response = client.get(f"/{settings.ADMIN_URL}")

    content = response.content.decode()
    assert "dark_mode.css" not in content
    assert "theme.js" not in content
    assert "theme-toggle" not in content
