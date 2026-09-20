"""Panel redakcyjny `ai_content`: singleton `AIProviderSettings` (wzorem `about`)
+ formularz generowania `PostGeneratorAdmin`."""

from typing import Any
from unittest.mock import patch

import pytest
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import Permission
from django.contrib.messages import get_messages
from django.test import RequestFactory

from ai_content.admin import AIProviderSettingsAdmin
from ai_content.models import AIProviderSettings
from ai_content.schemas import GeneratedPostContent
from ai_content.services import PostGenerationError
from blog.constants import Language, PostStatus
from blog.models import Post, PostTranslation

pytestmark = pytest.mark.django_db


# --- AIProviderSettingsAdmin: singleton, wzorem about/tests/test_admin.py ---


@pytest.fixture
def ai_provider_settings_admin() -> AIProviderSettingsAdmin:
    return AIProviderSettingsAdmin(AIProviderSettings, AdminSite())


@pytest.fixture
def superuser_request(django_user_model: Any) -> Any:
    user = django_user_model.objects.create_superuser(
        username="redaktorka-ai-superuser", password="haslo-testowe-123"
    )
    request = RequestFactory().get("/")
    request.user = user
    return request


def test_dodanie_dozwolone_gdy_singleton_nie_istnieje(
    ai_provider_settings_admin: AIProviderSettingsAdmin, superuser_request: Any
) -> None:
    assert ai_provider_settings_admin.has_add_permission(superuser_request) is True


def test_dodanie_zablokowane_gdy_singleton_juz_istnieje(
    ai_provider_settings_admin: AIProviderSettingsAdmin,
    superuser_request: Any,
    ai_provider_settings: AIProviderSettings,
) -> None:
    assert ai_provider_settings_admin.has_add_permission(superuser_request) is False


def test_lista_przekierowuje_do_edycji_gdy_singleton_istnieje(
    client: Any, django_user_model: Any, settings: Any, ai_provider_settings: AIProviderSettings
) -> None:
    user = django_user_model.objects.create_user(
        username="redaktorka-ai", password="haslo-testowe-123", is_staff=True, is_superuser=True
    )
    client.force_login(user)

    response = client.get(f"/{settings.ADMIN_URL}ai_content/aiprovidersettings/")

    assert response.status_code == 302
    assert (
        response.url
        == f"/{settings.ADMIN_URL}ai_content/aiprovidersettings/{ai_provider_settings.pk}/change/"
    )


def test_lista_przekierowuje_do_dodania_gdy_brak_singletona(
    client: Any, django_user_model: Any, settings: Any
) -> None:
    user = django_user_model.objects.create_user(
        username="redaktorka-ai", password="haslo-testowe-123", is_staff=True, is_superuser=True
    )
    client.force_login(user)

    response = client.get(f"/{settings.ADMIN_URL}ai_content/aiprovidersettings/")

    assert response.status_code == 302
    assert response.url == f"/{settings.ADMIN_URL}ai_content/aiprovidersettings/add/"


def test_changelist_zwraca_403_dla_staff_bez_uprawnien(
    client: Any, django_user_model: Any, settings: Any, ai_provider_settings: AIProviderSettings
) -> None:
    staff_without_permissions = django_user_model.objects.create_user(
        username="staff-bez-uprawnien-ai", password="haslo-testowe-123", is_staff=True
    )
    client.force_login(staff_without_permissions)

    response = client.get(f"/{settings.ADMIN_URL}ai_content/aiprovidersettings/")

    assert response.status_code == 403


def test_changelist_nadal_przekierowuje_do_edycji_dla_uprawnionego_konta(
    client: Any, django_user_model: Any, settings: Any, ai_provider_settings: AIProviderSettings
) -> None:
    staff_with_permissions = django_user_model.objects.create_user(
        username="redaktorka-ai-z-uprawnieniami", password="haslo-testowe-123", is_staff=True
    )
    staff_with_permissions.user_permissions.add(
        *Permission.objects.filter(
            content_type__app_label="ai_content",
            codename__in=["view_aiprovidersettings", "change_aiprovidersettings"],
        )
    )
    client.force_login(staff_with_permissions)

    response = client.get(f"/{settings.ADMIN_URL}ai_content/aiprovidersettings/")

    assert response.status_code == 302
    assert (
        response.url
        == f"/{settings.ADMIN_URL}ai_content/aiprovidersettings/{ai_provider_settings.pk}/change/"
    )


# --- PostGeneratorAdmin ------------------------------------------------------


def _post_generator_url(settings: Any) -> str:
    return f"/{settings.ADMIN_URL}ai_content/postgenerator/"


def test_get_z_uprawnieniem_zwraca_200_z_formularzem(
    client: Any, settings: Any, staff_with_add_post_permission: Any
) -> None:
    client.force_login(staff_with_add_post_permission)

    response = client.get(_post_generator_url(settings))

    assert response.status_code == 200
    content = response.content.decode()
    assert 'id="id_topic"' in content
    assert 'id="id_local_focus"' in content


def test_get_bez_uprawnienia_zwraca_403(
    client: Any, settings: Any, staff_without_add_post_permission: Any
) -> None:
    client.force_login(staff_without_add_post_permission)

    response = client.get(_post_generator_url(settings))

    assert response.status_code == 403


def test_get_z_samym_add_post_bez_change_post_zwraca_403(
    client: Any, settings: Any, django_user_model: Any
) -> None:
    """`add_post` bez `change_post` to za mało — sukces generowania i tak
    przekierowałby na `admin:blog_post_change`, którego to konto nie mogłoby
    otworzyć (`ai_content.admin.PostGeneratorAdmin._can_generate`)."""
    user = django_user_model.objects.create_user(
        username="staff-tylko-add-post", password="haslo-testowe-123", is_staff=True
    )
    user.user_permissions.add(
        Permission.objects.get(content_type__app_label="blog", codename="add_post")
    )
    client.force_login(user)

    response = client.get(_post_generator_url(settings))

    assert response.status_code == 403


def test_post_z_sukcesem_tworzy_post_i_przekierowuje_z_komunikatem(
    client: Any,
    settings: Any,
    staff_with_add_post_permission: Any,
    ai_provider_settings: AIProviderSettings,
    mock_generated_content: GeneratedPostContent,
) -> None:
    client.force_login(staff_with_add_post_permission)

    with patch(
        "ai_content.admin.generate_post_content", return_value=mock_generated_content
    ) as mocked:
        response = client.post(
            _post_generator_url(settings),
            data={"topic": "Soczewki kontaktowe", "local_focus": "Wrocław, Polska"},
        )

    mocked.assert_called_once()
    assert Post.objects.count() == 1
    post = Post.objects.get()
    assert post.author_id == staff_with_add_post_permission.pk
    translation = PostTranslation.objects.get(master=post, language_code=Language.PL)
    assert translation.status == PostStatus.DRAFT
    assert translation.title == mock_generated_content.title

    assert response.status_code == 302
    assert response.url == f"/{settings.ADMIN_URL}blog/post/{post.pk}/change/"

    # Czytamy zakolejkowany komunikat wprost z `request._messages`, zamiast
    # `follow=True` na redirect — nie testujemy tu zachowania widoku edycji
    # posta (`blog.admin.PostAdmin`), tylko że `PostGeneratorAdmin` zapisał
    # właściwy komunikat.
    messages = [str(message) for message in get_messages(response.wsgi_request)]
    assert len(messages) == 1
    assert f"/{settings.ADMIN_URL}blog/post/{post.pk}/change/" in messages[0]
    assert mock_generated_content.seo_rationale in messages[0]


def test_post_bez_skonfigurowanego_dostawcy_ai_nie_tworzy_posta(
    client: Any, settings: Any, staff_with_add_post_permission: Any
) -> None:
    """Bez fixture `ai_provider_settings` — `AIProviderSettings.objects.first()` zwraca `None`."""
    client.force_login(staff_with_add_post_permission)

    response = client.post(
        _post_generator_url(settings),
        data={"topic": "Soczewki kontaktowe", "local_focus": "Wrocław, Polska"},
    )

    assert response.status_code == 200
    content = response.content.decode()
    assert "Najpierw skonfiguruj dostawcę AI" in content
    assert Post.objects.count() == 0
    assert 'id="id_topic"' in content


def test_post_z_bledem_generowania_pokazuje_komunikat_i_zachowuje_temat(
    client: Any,
    settings: Any,
    staff_with_add_post_permission: Any,
    ai_provider_settings: AIProviderSettings,
) -> None:
    client.force_login(staff_with_add_post_permission)

    with patch(
        "ai_content.admin.generate_post_content",
        side_effect=PostGenerationError("Nie udało się wygenerować treści posta."),
    ):
        response = client.post(
            _post_generator_url(settings),
            data={"topic": "Soczewki kontaktowe dla dzieci", "local_focus": "Wrocław, Polska"},
        )

    assert response.status_code == 200
    content = response.content.decode()
    assert "Nie udało się wygenerować treści posta." in content
    assert Post.objects.count() == 0
    assert 'value="Soczewki kontaktowe dla dzieci"' in content
