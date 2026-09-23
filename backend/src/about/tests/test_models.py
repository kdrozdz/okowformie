"""Niezmienniki modeli `about`: singleton, sanityzacja, publikacja, certyfikaty."""

from collections.abc import Callable

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from about.models import AboutMe, AboutMeTranslation, Certificate
from core.constants import Language, PublicationStatus

pytestmark = pytest.mark.django_db


# --- Singleton ------------------------------------------------------------


def test_pierwszy_zapis_laduje_pod_pk_1() -> None:
    about = AboutMe.objects.create(full_name="Jan Kowalski")

    assert about.pk == AboutMe.SINGLETON_ID


def test_kolejny_zapis_nadpisuje_ten_sam_wiersz_zamiast_tworzyc_drugi() -> None:
    """`save()` wymusza `pk=1` niezależnie od tego, jak powstaje instancja —
    nawet z pominięciem panelu (shell, fixture, import).

    `AboutMe(...).save()`, nie `.objects.create(...)`: `create()` przekazuje
    `force_insert=True`, więc druga instancja wywaliłaby się na ograniczeniu
    unikalności klucza głównego zamiast zaktualizować istniejący wiersz —
    to jest oczekiwane zachowanie Django dla jawnego "utwórz nowy", a
    edytor panelu i tak zawsze woła zwykłe `save()` (przez `ModelForm`).
    """
    AboutMe(full_name="Pierwsza wersja").save()
    AboutMe(full_name="Druga wersja").save()

    assert AboutMe.objects.count() == 1
    assert AboutMe.objects.get().full_name == "Druga wersja"


# --- Sanityzacja bio --------------------------------------------------------


def test_zapis_czysci_bio(make_about: Callable[..., AboutMe]) -> None:
    about = make_about(pl={"bio": '<p>Ok</p><script>alert("xss")</script>'})

    stored = about.translations.get(language_code=Language.PL).bio
    assert "<script" not in stored
    assert "<p>Ok</p>" in stored


def test_odczyt_czysci_bio_wpisane_z_pominieciem_save(make_about: Callable[..., AboutMe]) -> None:
    """Druga warstwa obrony: wiersz wstawiony bez `save()` też nie wycieka."""
    about = make_about(pl={})
    AboutMeTranslation.objects.filter(master=about, language_code=Language.PL).update(
        bio='<img src="x" onerror="alert(1)">'
    )

    translation = AboutMeTranslation.objects.get(master=about, language_code=Language.PL)

    assert "onerror" in translation.bio  # surowa kolumna faktycznie skażona
    assert "onerror" not in translation.bio_html


# --- Publikacja -------------------------------------------------------------


def test_publikacja_stempluje_date(make_about: Callable[..., AboutMe]) -> None:
    before = timezone.now()
    about = make_about(pl={"status": PublicationStatus.PUBLISHED})

    published_at = about.translations.get(language_code=Language.PL).published_at
    assert published_at is not None
    assert published_at >= before


def test_szkic_nie_ma_daty_publikacji(make_about: Callable[..., AboutMe]) -> None:
    about = make_about(pl={"status": PublicationStatus.DRAFT})

    assert about.translations.get(language_code=Language.PL).published_at is None


def test_archiwizacja_nie_kasuje_daty_publikacji(make_about: Callable[..., AboutMe]) -> None:
    about = make_about(pl={"status": PublicationStatus.PUBLISHED})
    translation = about.translations.get(language_code=Language.PL)
    original = translation.published_at

    translation.status = PublicationStatus.ARCHIVED
    translation.save()

    translation.refresh_from_db()
    assert translation.published_at == original


def test_status_jest_niezalezny_miedzy_jezykami(make_about: Callable[..., AboutMe]) -> None:
    about = make_about(
        pl={"status": PublicationStatus.PUBLISHED},
        en={"status": PublicationStatus.DRAFT},
    )

    statuses = {t.language_code: t.status for t in about.translations.all()}
    assert statuses == {
        Language.PL: PublicationStatus.PUBLISHED,
        Language.EN: PublicationStatus.DRAFT,
    }


# --- Fallbacki SEO ------------------------------------------------------


def test_seo_wpada_na_naglowek_gdy_pola_puste(make_about: Callable[..., AboutMe]) -> None:
    about = make_about(pl={"headline": "Nagłówek"})

    translation = about.translations.get(language_code=Language.PL)
    assert translation.seo_title == "Nagłówek"
    assert translation.seo_description == "Nagłówek"


def test_seo_uzywa_nadpisan_gdy_sa(make_about: Callable[..., AboutMe]) -> None:
    about = make_about(pl={"meta_title": "Inny tytuł", "meta_description": "Inny opis"})

    translation = about.translations.get(language_code=Language.PL)
    assert translation.seo_title == "Inny tytuł"
    assert translation.seo_description == "Inny opis"


# --- Certyfikaty --------------------------------------------------------


def test_certyfikaty_sa_posortowane_po_order(
    make_about: Callable[..., AboutMe], make_certificate: Callable[..., Certificate]
) -> None:
    about = make_about(pl={})
    third = make_certificate(about, name="Trzeci", order=2)
    first = make_certificate(about, name="Pierwszy", order=0)
    second = make_certificate(about, name="Drugi", order=1)

    assert list(about.certificates.all()) == [first, second, third]


def test_certyfikat_bez_zdjecia_jest_poprawny(
    make_about: Callable[..., AboutMe], make_certificate: Callable[..., Certificate]
) -> None:
    about = make_about(pl={})
    certificate = make_certificate(about)

    assert not certificate.image


@pytest.mark.parametrize("year", [1900, 2999])
def test_rok_spoza_zakresu_jest_odrzucany(
    make_about: Callable[..., AboutMe], year: int
) -> None:
    about = make_about(pl={})
    certificate = Certificate(about=about, name="X", issuer="Y", issued_year=year)

    with pytest.raises(ValidationError):
        certificate.full_clean()


def test_rok_w_zakresie_przechodzi(make_about: Callable[..., AboutMe]) -> None:
    about = make_about(pl={})
    certificate = Certificate(about=about, name="X", issuer="Y", issued_year=timezone.now().year)

    certificate.full_clean()  # nie podnosi wyjątku


def test_issuer_ma_help_text() -> None:
    """`issuer` był jedynym polem certyfikatu bez opisu, obok `name`/`image`/
    `order`, które go mają (`docs/tasks/15-motyw-panelu-admina.md`) — sanity
    check obecności, nie treści słowo w słowo (żeby nie być kruchym na
    przyszłe redagowanie tekstu)."""
    help_text = Certificate._meta.get_field("issuer").help_text

    assert help_text
