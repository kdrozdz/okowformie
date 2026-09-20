"""Wspólne fixture'y testów `ai_content`."""

from typing import Any

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission

from ai_content.constants import AIProvider
from ai_content.models import AIProviderSettings
from ai_content.schemas import GeneratedPostContent


@pytest.fixture
def author(db: Any) -> Any:
    """Autor postów — używany jako `author=` w `create_draft_post_from_generated_content`.

    `blog/tests/conftest.py` ma analogiczną fixture, ale pytest nie dzieli
    `conftest.py` między katalogami sióstr (`ai_content/tests/`
    vs `blog/tests/`), stąd osobna definicja tutaj.
    """
    return get_user_model().objects.create_user(
        username="redaktorka-ai-content", password="haslo-testowe-123"
    )


@pytest.fixture
def ai_provider_settings(db: Any) -> AIProviderSettings:
    """Skonfigurowany dostawca AI — wartości mieszczące się w walidatorach modelu."""
    return AIProviderSettings.objects.create(
        provider=AIProvider.ANTHROPIC,
        model_name="claude-test",
        temperature=0.7,
        max_output_tokens=4000,
    )


@pytest.fixture
def mock_generated_content() -> GeneratedPostContent:
    """Gotowy `GeneratedPostContent` do wstrzyknięcia w zamockowany serwis.

    Wartości celowo krótkie i dobrze mieszczące się w limitach pól
    (`ai_content/schemas.py`), żeby nie kolidowały z walidacją Pydantic ani
    `full_clean()` na `PostTranslation`.
    """
    return GeneratedPostContent(
        title="Jak dobrać soczewki kontaktowe na jesień",
        excerpt="Krótki poradnik o doborze soczewek kontaktowych na chłodniejsze miesiące.",
        content="<p>Jesienią warto zwrócić uwagę na nawilżenie oczu.</p>",
        meta_title="Soczewki kontaktowe jesienią — poradnik",
        meta_description=(
            "Dowiedz się, jak dobrać soczewki kontaktowe na jesień i zadbać o komfort oczu "
            "w chłodniejsze dni. Praktyczne wskazówki optometrysty."
        ),
        cover_image_alt="Osoba zakładająca soczewkę kontaktową przed lustrem",
        seo_rationale=(
            "Fraza „soczewki kontaktowe jesienią” ma sezonowe zainteresowanie wyszukiwarek."
        ),
    )


@pytest.fixture
def staff_with_add_post_permission(django_user_model: Any) -> Any:
    """Staff z uprawnieniem `blog.add_post` — dostęp do zakładki „Post z AI”."""
    user = django_user_model.objects.create_user(
        username="redaktorka-ai", password="haslo-testowe-123", is_staff=True
    )
    user.user_permissions.add(
        Permission.objects.get(content_type__app_label="blog", codename="add_post")
    )
    return user


@pytest.fixture
def staff_without_add_post_permission(django_user_model: Any) -> Any:
    """Staff bez uprawnienia `blog.add_post` — zakładka „Post z AI” niedostępna."""
    return django_user_model.objects.create_user(
        username="staff-bez-uprawnien", password="haslo-testowe-123", is_staff=True
    )
