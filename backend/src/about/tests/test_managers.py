"""Widoczność publiczna: `AboutMeManager.get_published` (`.claude/rules/security.md`)."""

from collections.abc import Callable

import pytest

from about.models import AboutMe
from core.constants import Language, PublicationStatus

pytestmark = pytest.mark.django_db


def test_brak_singletona_daje_does_not_exist() -> None:
    with pytest.raises(AboutMe.DoesNotExist):
        AboutMe.objects.get_published(Language.PL)


def test_szkic_nie_jest_widoczny_publicznie(make_about: Callable[..., AboutMe]) -> None:
    make_about(pl={"status": PublicationStatus.DRAFT})

    with pytest.raises(AboutMe.DoesNotExist):
        AboutMe.objects.get_published(Language.PL)


def test_archiwum_nie_jest_widoczne_publicznie(make_about: Callable[..., AboutMe]) -> None:
    make_about(pl={"status": PublicationStatus.ARCHIVED})

    with pytest.raises(AboutMe.DoesNotExist):
        AboutMe.objects.get_published(Language.PL)


def test_opublikowana_strona_jest_widoczna(make_about: Callable[..., AboutMe]) -> None:
    about = make_about(pl={"status": PublicationStatus.PUBLISHED})

    assert AboutMe.objects.get_published(Language.PL) == about


def test_brak_tlumaczenia_en_nie_wypada_na_polska_tresc(make_about: Callable[..., AboutMe]) -> None:
    make_about(pl={"status": PublicationStatus.PUBLISHED}, en=None)

    with pytest.raises(AboutMe.DoesNotExist):
        AboutMe.objects.get_published(Language.EN)


def test_en_w_szkicu_nie_jest_widoczne(make_about: Callable[..., AboutMe]) -> None:
    make_about(
        pl={"status": PublicationStatus.PUBLISHED},
        en={"status": PublicationStatus.DRAFT},
    )

    with pytest.raises(AboutMe.DoesNotExist):
        AboutMe.objects.get_published(Language.EN)
