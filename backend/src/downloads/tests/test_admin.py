"""Panel redakcyjny: lista się renderuje i pokazuje status per język
(`.claude/rules/content-admin.md`)."""

from collections.abc import Callable
from typing import Any

import pytest

from core.constants import PublicationStatus
from downloads.models import Download

pytestmark = pytest.mark.django_db


@pytest.fixture
def staff_client(client: Any, django_user_model: Any) -> Any:
    user = django_user_model.objects.create_user(
        username="redaktorka", password="haslo-testowe-123", is_staff=True, is_superuser=True
    )
    client.force_login(user)
    return client


def test_lista_sie_renderuje(
    staff_client: Any, settings: Any, make_download: Callable[..., Download]
) -> None:
    make_download(pl={"title": "Cennik badań"})

    response = staff_client.get(f"/{settings.ADMIN_URL}downloads/download/")

    assert response.status_code == 200
    assert "Cennik badań" in response.content.decode()


def test_lista_pokazuje_status_per_jezyk(
    staff_client: Any, settings: Any, make_download: Callable[..., Download]
) -> None:
    make_download(pl={"title": "Cennik", "status": PublicationStatus.PUBLISHED}, en=None)

    response = staff_client.get(f"/{settings.ADMIN_URL}downloads/download/")
    content = response.content.decode()

    assert "Opublikowany" in content
    assert "brak wersji" in content


def test_formularz_dodawania_sie_renderuje(staff_client: Any, settings: Any) -> None:
    response = staff_client.get(f"/{settings.ADMIN_URL}downloads/download/add/")

    assert response.status_code == 200
