"""Panel redakcyjny `AboutMe`: walidacja uploadu obrazu na poziomie formularza.

Analogiczne do `blog/tests/test_admin_form.py::test_plik_z_podmieniona_zawartoscia_...`
— `core.validators.validate_image_upload` sprawdza rozszerzenie, rozmiar **i**
faktyczną zawartość (Pillow), więc plik, którego treść nie jest w ogóle
obrazem, jest odrzucany niezależnie od tego, że nazwa ma dozwolone
rozszerzenie i niezależnie od tego, kto woła walidator (formularz czy
`Model.full_clean()` bezpośrednio — patrz
`test_certificate_full_clean_wykrywa_podmieniona_zawartosc`).
"""

from collections.abc import Callable
from typing import Any

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile

from about.forms import AboutMeAdminForm
from about.models import AboutMe, Certificate
from core.constants import Language, PublicationStatus

pytestmark = pytest.mark.django_db


def build_form(
    *,
    language_code: str = Language.PL,
    instance: AboutMe | None = None,
    files: dict[str, Any] | None = None,
    **overrides: Any,
) -> AboutMeAdminForm:
    data: dict[str, Any] = {
        "full_name": "Jan Kowalski",
        "headline": "Optometrysta",
        "bio": "<p>Bio</p>",
        "photo_alt": "",
        "meta_title": "",
        "meta_description": "",
        "status": PublicationStatus.DRAFT,
        "published_at": "",
    }
    data.update(overrides)

    form_class = type(
        "BoundAboutMeAdminForm", (AboutMeAdminForm,), {"language_code": language_code}
    )
    return form_class(data=data, instance=instance, files=files)


def test_poprawny_formularz_przechodzi() -> None:
    form = build_form()

    assert form.is_valid(), form.errors


def test_podmieniona_zawartosc_pliku_zdjecia_jest_odrzucana() -> None:
    """`.jpg` z treścią, która nie jest obrazem, nie może przejść tylko dlatego,
    że nazwa pliku wygląda poprawnie — ta sama luka co przy `Post.cover_image`."""
    fake_jpg = SimpleUploadedFile("zdjecie.jpg", b"<?php echo 'pwn'; ?>", content_type="image/jpeg")
    form = build_form(files={"photo": fake_jpg})

    assert not form.is_valid()
    assert "photo" in form.errors


def test_bardzo_dlugi_naglowek_jest_odrzucany() -> None:
    """`headline.max_length == 200` — obowiązkowy przypadek brzegowy
    (`.claude/rules/conventions.md`), analogiczny do
    `blog/tests/test_admin_form.py::test_bardzo_dlugi_tytul_jest_odrzucany`."""
    form = build_form(headline="A" * 300)

    assert not form.is_valid()
    assert "headline" in form.errors


def test_pusty_naglowek_daje_przyjazny_komunikat() -> None:
    """`headline` jest wymagany bezwarunkowo na poziomie pola modelu — Django
    odrzuca go, zanim `AboutMeAdminForm.clean()` się wykona. Komunikat musi
    więc pochodzić z `Meta.error_messages`, nie z generycznego „To pole jest
    wymagane" (defekt #2, `docs/tasks/9-strona-o-mnie.md`)."""
    form = build_form(headline="")

    assert not form.is_valid()
    message = " ".join(form.errors["headline"])
    assert "Nagłówek jest wymagany" in message
    assert message != "To pole jest wymagane."


def test_zbyt_dlugi_tytul_seo_daje_przyjazny_komunikat() -> None:
    """`meta_title.max_length == META_TITLE_MAX_LENGTH` odrzuca wartość na
    poziomie pola formularza — przyjazny komunikat musi pochodzić z
    `Meta.error_messages`, bo `_validate_seo` już nigdy go dla tego
    przypadku nie zobaczy w `cleaned_data` (defekt #2)."""
    form = build_form(meta_title="A" * 100)

    assert not form.is_valid()
    message = " ".join(form.errors["meta_title"])
    assert "Skróć go" in message
    assert "wyszukiwarka" in message
    assert "Upewnij się" not in message  # generyczny komunikat Django


def test_zbyt_dlugi_opis_seo_daje_przyjazny_komunikat() -> None:
    """Analogicznie do tytułu SEO, ale dla `meta_description`."""
    form = build_form(meta_description="A" * 300)

    assert not form.is_valid()
    message = " ".join(form.errors["meta_description"])
    assert "ucięty w połowie zdania" in message
    assert "Upewnij się" not in message


def test_meta_title_i_meta_description_maja_powiekszone_widgety() -> None:
    """Ten sam wzorzec co `blog.forms.PostAdminForm`
    (`docs/tasks/15-motyw-panelu-admina.md`)."""
    form = build_form()

    assert form.fields["meta_title"].widget.attrs.get("size") == 80
    assert form.fields["meta_description"].widget.attrs.get("rows") == 3


def test_bardzo_dlugie_imie_i_nazwisko_jest_odrzucane() -> None:
    """`full_name.max_length == 200` — pole wspólne, nie tłumaczone, ale ten
    sam niezmiennik: redaktor wklejający zbyt długi tekst dostaje czytelny
    błąd formularza, nie `DataError` z bazy."""
    form = build_form(full_name="A" * 300)

    assert not form.is_valid()
    assert "full_name" in form.errors


def test_certificate_full_clean_wykrywa_podmieniona_zawartosc(
    make_about: Callable[..., AboutMe],
) -> None:
    """Defekt #3 (`docs/tasks/9-strona-o-mnie.md`), naprawiony: wcześniej
    `core.validators.validate_image_upload` sprawdzał tylko rozszerzenie i
    rozmiar, a weryfikacja treści przez Pillow żyła wyłącznie w automatycznym
    `forms.ImageField` z `ModelForm` — wywołanie walidacji **bezpośrednio na
    modelu** (`full_clean()`, z pominięciem panelu) nie wykrywało podmienionej
    zawartości. Walidator sam otwiera i weryfikuje treść obrazu teraz, więc
    `full_clean()` łapie to samo, co panel (patrz test poniżej, który
    POST-uje przez HTTP i sprawdza tę samą ochronę na realnej ścieżce
    zapisu)."""
    about = make_about(pl={})
    fake_png = SimpleUploadedFile("certyfikat.png", b"nie jestem obrazem", content_type="image/png")
    certificate = Certificate(
        about=about,
        name="European Diploma in Optometry",
        issuer="ECOO",
        issued_year=2020,
        image=fake_png,
    )

    with pytest.raises(ValidationError) as error:
        certificate.full_clean()

    assert "image" in error.value.message_dict


def test_admin_odrzuca_podmieniona_zawartosc_zdjecia_certyfikatu_przez_http(
    client: Any,
    django_user_model: Any,
    settings: Any,
    make_about: Callable[..., AboutMe],
) -> None:
    """Realna droga zapisu certyfikatu (panel, `CertificateInline`) faktycznie
    łapie podmienioną zawartość — to `forms.ImageField` wygenerowany
    automatycznie przez `TabularInline`, ten sam mechanizm Pillow, co przy
    `AboutMe.photo`. Test dokumentuje, że TA warstwa (nie `full_clean()`) jest
    jedyną faktyczną obroną dla certyfikatów."""
    user = django_user_model.objects.create_user(
        username="redaktorka", password="haslo-testowe-123", is_staff=True, is_superuser=True
    )
    client.force_login(user)
    about = make_about(pl={"headline": "Optometrysta"})

    fake_png = SimpleUploadedFile("certyfikat.png", b"nie jestem obrazem", content_type="image/png")
    data = {
        "full_name": "Jan Kowalski",
        "headline": "Optometrysta",
        "bio": "<p>Bio</p>",
        "photo_alt": "",
        "meta_title": "",
        "meta_description": "",
        "status": PublicationStatus.DRAFT,
        "published_at": "",
        "certificates-TOTAL_FORMS": "1",
        "certificates-INITIAL_FORMS": "0",
        "certificates-MIN_NUM_FORMS": "0",
        "certificates-MAX_NUM_FORMS": "1000",
        "certificates-0-about": str(about.pk),
        "certificates-0-name": "European Diploma in Optometry",
        "certificates-0-issuer": "ECOO",
        "certificates-0-issued_year": "2020",
        "certificates-0-order": "0",
        "_save": "Zapisz",
    }
    files = {"certificates-0-image": fake_png}

    response = client.post(
        f"/{settings.ADMIN_URL}about/aboutme/{about.pk}/change/?language=pl",
        data={**data, **files},
    )

    assert response.status_code == 200, (
        "Oczekiwano 200 (formularz z błędem walidacji obrazu), a dostano "
        f"{response.status_code} — certyfikat z fałszywą treścią pliku "
        "prawdopodobnie został zapisany."
    )
    assert Certificate.objects.count() == 0
    content = response.content.decode()
    assert "obraz" in content.lower() or "image" in content.lower()
