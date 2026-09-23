"""Panel redakcyjny: lista się renderuje i pokazuje status per język
(`.claude/rules/content-admin.md`)."""

import re
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


def _change_link_pks(content: str) -> list[str]:
    """Liczba faktycznych wierszy na liście — po linkach `.../download/{pk}/change/`,
    nie po wystąpieniach tytułu (który Django renderuje dwa razy na wiersz:
    w `aria-label`/tooltipie checkboksa i w tekście linku)."""
    return re.findall(r"/download/(\d+)/change/", content)


def test_filtr_statusu_nie_duplikuje_pliku_z_dwoma_tlumaczeniami(
    staff_client: Any, settings: Any, published_download: Download
) -> None:
    """`list_filter = ("translations__status",)` robi JOIN na `translations`
    — bez `DownloadAdmin.get_queryset().distinct()` plik z dwoma
    opublikowanymi tłumaczeniami (PL+EN) pojawiłby się na liście dwa razy.
    """
    response = staff_client.get(
        f"/{settings.ADMIN_URL}downloads/download/?translations__status=published"
    )

    assert response.status_code == 200
    assert _change_link_pks(response.content.decode()) == [str(published_download.pk)]


def test_sortowanie_po_nazwie_nie_duplikuje_pliku_z_dwoma_tlumaczeniami(
    staff_client: Any, settings: Any, published_download: Download
) -> None:
    """`admin_title` celowo nie ma `ordering="translations__title"` (patrz
    docstring w `downloads/admin.py`) — `?o=1` (próba sortowania po tej
    kolumnie) nie ma więc efektu i nie duplikuje wierszy, w przeciwieństwie
    do tego, co dałoby naiwne sortowanie po polu z JOIN-a.
    """
    response = staff_client.get(f"/{settings.ADMIN_URL}downloads/download/?o=1")

    assert response.status_code == 200
    assert _change_link_pks(response.content.decode()) == [str(published_download.pk)]
