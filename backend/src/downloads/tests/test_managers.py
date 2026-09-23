"""Widoczność publiczna: `DownloadManager.published` (`.claude/rules/security.md`)."""

from collections.abc import Callable

import pytest

from core.constants import Language, PublicationStatus
from downloads.models import Download

pytestmark = pytest.mark.django_db


def test_brak_plikow_daje_pusty_wynik() -> None:
    assert list(Download.objects.published(Language.PL)) == []


def test_szkic_nie_jest_widoczny(make_download: Callable[..., Download]) -> None:
    make_download(pl={"status": PublicationStatus.DRAFT})

    assert list(Download.objects.published(Language.PL)) == []


def test_archiwum_nie_jest_widoczne(make_download: Callable[..., Download]) -> None:
    make_download(pl={"status": PublicationStatus.ARCHIVED})

    assert list(Download.objects.published(Language.PL)) == []


def test_opublikowany_plik_jest_widoczny(make_download: Callable[..., Download]) -> None:
    download = make_download(pl={"status": PublicationStatus.PUBLISHED})

    assert list(Download.objects.published(Language.PL)) == [download]


def test_brak_tlumaczenia_en_nie_wypada_na_polska_tresc(
    make_download: Callable[..., Download],
) -> None:
    make_download(pl={"status": PublicationStatus.PUBLISHED}, en=None)

    assert list(Download.objects.published(Language.EN)) == []


def test_en_w_szkicu_nie_jest_widoczne(make_download: Callable[..., Download]) -> None:
    make_download(
        pl={"status": PublicationStatus.PUBLISHED},
        en={"status": PublicationStatus.DRAFT},
    )

    assert list(Download.objects.published(Language.EN)) == []


def test_wyniki_sa_posortowane_po_order(make_download: Callable[..., Download]) -> None:
    third = make_download(order=2, pl={"status": PublicationStatus.PUBLISHED})
    first = make_download(order=0, pl={"status": PublicationStatus.PUBLISHED})
    second = make_download(order=1, pl={"status": PublicationStatus.PUBLISHED})

    assert list(Download.objects.published(Language.PL)) == [first, second, third]
