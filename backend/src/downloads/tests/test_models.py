"""Niezmienniki modeli `downloads`: publikacja, unikalność tłumaczenia."""

from collections.abc import Callable

import pytest
from django.db import IntegrityError, transaction
from django.utils import timezone

from core.constants import Language, PublicationStatus
from downloads.models import Download, DownloadTranslation

pytestmark = pytest.mark.django_db


# --- Publikacja -------------------------------------------------------------


def test_publikacja_stempluje_date(make_download: Callable[..., Download]) -> None:
    before = timezone.now()
    download = make_download(pl={"status": PublicationStatus.PUBLISHED})

    published_at = download.translations.get(language_code=Language.PL).published_at
    assert published_at is not None
    assert published_at >= before


def test_szkic_nie_ma_daty_publikacji(make_download: Callable[..., Download]) -> None:
    download = make_download(pl={"status": PublicationStatus.DRAFT})

    assert download.translations.get(language_code=Language.PL).published_at is None


def test_archiwizacja_nie_kasuje_daty_publikacji(make_download: Callable[..., Download]) -> None:
    download = make_download(pl={"status": PublicationStatus.PUBLISHED})
    translation = download.translations.get(language_code=Language.PL)
    original = translation.published_at

    translation.status = PublicationStatus.ARCHIVED
    translation.save()

    translation.refresh_from_db()
    assert translation.published_at == original


def test_cofniecie_do_szkicu_nie_kasuje_daty_publikacji(
    make_download: Callable[..., Download],
) -> None:
    download = make_download(pl={"status": PublicationStatus.PUBLISHED})
    translation = download.translations.get(language_code=Language.PL)
    original = translation.published_at

    translation.status = PublicationStatus.DRAFT
    translation.save()

    translation.refresh_from_db()
    assert translation.published_at == original


def test_status_jest_niezalezny_miedzy_jezykami(make_download: Callable[..., Download]) -> None:
    download = make_download(
        pl={"status": PublicationStatus.PUBLISHED},
        en={"status": PublicationStatus.DRAFT},
    )

    statuses = {t.language_code: t.status for t in download.translations.all()}
    assert statuses == {
        Language.PL: PublicationStatus.PUBLISHED,
        Language.EN: PublicationStatus.DRAFT,
    }


# --- Unikalność tłumaczenia ---------------------------------------------


def test_tlumaczenie_jest_unikalne_per_jezyk(make_download: Callable[..., Download]) -> None:
    download = make_download(pl={})

    with pytest.raises(IntegrityError), transaction.atomic():
        DownloadTranslation.objects.create(
            master=download, language_code=Language.PL, title="Duplikat"
        )


def test_ten_sam_jezyk_moze_istniec_dla_dwoch_roznych_plikow(
    make_download: Callable[..., Download],
) -> None:
    """Unikalność jest per (master, język), nie globalnie po języku."""
    first = make_download(pl={"title": "Pierwszy"})
    second = make_download(pl={"title": "Drugi"})

    assert first.translations.get(language_code=Language.PL).title == "Pierwszy"
    assert second.translations.get(language_code=Language.PL).title == "Drugi"
