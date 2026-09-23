"""Panel redakcyjny: walidacja mówi po polsku i mówi, co zrobić."""

from collections.abc import Callable
from io import BytesIO
from typing import Any

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from blog.constants import Language, PostStatus
from blog.forms import PostAdminForm
from blog.models import Post

pytestmark = pytest.mark.django_db


def _valid_jpeg() -> SimpleUploadedFile:
    buffer = BytesIO()
    Image.new("RGB", (2, 2), color="red").save(buffer, format="JPEG")
    return SimpleUploadedFile("okladka.jpg", buffer.getvalue(), content_type="image/jpeg")


def build_form(
    author: Any,
    *,
    language_code: str = Language.PL,
    instance: Post | None = None,
    files: dict[str, Any] | None = None,
    **overrides: Any,
) -> PostAdminForm:
    data: dict[str, Any] = {
        "author": author.pk,
        "title": "Nalewka z pigwy",
        "slug": "",
        "excerpt": "Jak zrobić nalewkę z pigwy krok po kroku.",
        "content": "<p>Treść przepisu.</p>",
        "cover_image_alt": "",
        "meta_title": "",
        "meta_description": "",
        "status": PostStatus.DRAFT,
        "published_at": "",
    }
    data.update(overrides)

    form_class = type("BoundPostAdminForm", (PostAdminForm,), {"language_code": language_code})
    return form_class(data=data, instance=instance, files=files)


def test_poprawny_formularz_przechodzi(author: Any) -> None:
    form = build_form(author)

    assert form.is_valid(), form.errors


def test_slug_moze_zostac_pusty(author: Any) -> None:
    """Redaktor nigdy nie musi wpisywać slugu ręcznie."""
    form = build_form(author, slug="")
    assert form.is_valid(), form.errors

    post = form.save()

    assert post.translations.get(language_code=Language.PL).slug == "nalewka-z-pigwy"


def test_zajety_slug_daje_polski_komunikat_z_podpowiedzia(
    author: Any, make_post: Callable[..., Post]
) -> None:
    make_post(pl={"title": "Nalewka z pigwy", "slug": "nalewka-z-pigwy"})

    form = build_form(author, slug="nalewka-z-pigwy")

    assert not form.is_valid()
    message = " ".join(form.errors["slug"])
    assert "już zajęty" in message
    assert "nalewka-z-pigwy-2" in message


def test_ten_sam_slug_w_drugim_jezyku_przechodzi(
    author: Any, make_post: Callable[..., Post]
) -> None:
    make_post(pl={"title": "Gin", "slug": "gin"})

    form = build_form(author, language_code=Language.EN, slug="gin", title="Gin")

    assert form.is_valid(), form.errors


def test_publikacja_bez_tresci_jest_blokowana(author: Any) -> None:
    form = build_form(author, status=PostStatus.PUBLISHED, content="")

    assert not form.is_valid()
    message = " ".join(form.errors["status"])
    assert "Aby opublikować" in message
    assert "treść" in message


def test_publikacja_z_trescia_przechodzi(author: Any) -> None:
    form = build_form(author, status=PostStatus.PUBLISHED)

    assert form.is_valid(), form.errors


def test_za_krotki_opis_seo_mowi_ile_dopisac(author: Any) -> None:
    form = build_form(author, meta_description="Za krótki opis.")

    assert not form.is_valid()
    message = " ".join(form.errors["meta_description"])
    assert "Dopisz jeszcze co najmniej" in message


def test_opis_seo_w_zakresie_przechodzi(author: Any) -> None:
    form = build_form(author, meta_description="x" * 155)

    assert form.is_valid(), form.errors


def test_pusty_opis_seo_przechodzi(author: Any) -> None:
    """Puste pole SEO to nie błąd — zadziała fallback na zajawkę."""
    form = build_form(author, meta_description="")

    assert form.is_valid(), form.errors


def test_tresc_ze_skryptem_zapisuje_sie_oczyszczona(author: Any) -> None:
    form = build_form(author, content='<p>Ok</p><script>alert("xss")</script>')
    assert form.is_valid(), form.errors

    post = form.save()

    assert "<script" not in post.translations.get(language_code=Language.PL).content


def test_meta_title_i_meta_description_maja_powiekszone_widgety(author: Any) -> None:
    """Wcześniej domyślny, wąski `TextInput` mimo pola na pełne zdanie (do
    60/160 znaków) — niespójność z resztą pól tej długości w tym samym
    formularzu (`docs/tasks/15-motyw-panelu-admina.md`)."""
    form = build_form(author)

    assert form.fields["meta_title"].widget.attrs.get("size") == 80
    assert form.fields["meta_description"].widget.attrs.get("rows") == 3


def test_formularz_ma_pola_seo_i_status(author: Any) -> None:
    """Pola tłumaczone muszą realnie wejść do formularza, nie tylko do modelu."""
    form = build_form(author)

    for field in ("title", "slug", "excerpt", "content", "meta_title", "status"):
        assert field in form.fields, field


def test_bardzo_dlugi_tytul_jest_odrzucany(author: Any) -> None:
    """`title.max_length == 200` — Django waliduje to samo bez własnego kodu,
    ale to niezmiennik warty regresji: redaktor wklejający zbyt długi tytuł
    (np. z Worda) ma dostać czytelny błąd, a nie `DataError` z bazy."""
    form = build_form(author, title="A" * 300)

    assert not form.is_valid()
    assert "title" in form.errors


def test_pusty_tytul_daje_przyjazny_komunikat(author: Any) -> None:
    """`title` jest wymagany bezwarunkowo na poziomie pola modelu — Django
    odrzuca go, zanim `PostAdminForm.clean()` się wykona. Komunikat musi więc
    pochodzić z `Meta.error_messages`, nie z generycznego „To pole jest
    wymagane" (defekt #2, `docs/tasks/9-strona-o-mnie.md`)."""
    form = build_form(author, title="")

    assert not form.is_valid()
    message = " ".join(form.errors["title"])
    assert "Tytuł jest wymagany" in message
    assert message != "To pole jest wymagane."


def test_pusta_zajawka_daje_przyjazny_komunikat(author: Any) -> None:
    """Analogicznie do tytułu, ale dla `excerpt` (też wymagane bezwarunkowo)."""
    form = build_form(author, excerpt="")

    assert not form.is_valid()
    message = " ".join(form.errors["excerpt"])
    assert "Zajawka jest wymagana" in message


def test_zbyt_dlugi_tytul_seo_daje_przyjazny_komunikat(author: Any) -> None:
    """`meta_title.max_length == META_TITLE_MAX_LENGTH` odrzuca wartość na
    poziomie pola formularza — przyjazny komunikat musi pochodzić z
    `Meta.error_messages`, bo `_validate_seo` już nigdy go dla tego
    przypadku nie zobaczy w `cleaned_data` (defekt #2)."""
    form = build_form(author, meta_title="A" * 100)

    assert not form.is_valid()
    message = " ".join(form.errors["meta_title"])
    assert "Skróć go" in message
    assert "wyszukiwarka" in message
    assert "Upewnij się" not in message  # generyczny komunikat Django


def test_zbyt_dlugi_opis_seo_daje_przyjazny_komunikat(author: Any) -> None:
    """Analogicznie do tytułu SEO, ale dla `meta_description`."""
    form = build_form(author, meta_description="A" * 300)

    assert not form.is_valid()
    message = " ".join(form.errors["meta_description"])
    assert "ucięty w połowie zdania" in message
    assert "Upewnij się" not in message


def test_publikacja_bez_okladki_przechodzi(author: Any) -> None:
    """Brak obrazu okładki nie blokuje publikacji — `cover_image` jest
    opcjonalny, a wymóg `cover_image_alt` odpala się tylko, gdy okładka
    faktycznie jest przesłana."""
    form = build_form(author, status=PostStatus.PUBLISHED)

    assert form.is_valid(), form.errors


def test_plik_z_podmieniona_zawartoscia_pod_dozwolonym_rozszerzeniem_jest_odrzucany(
    author: Any,
) -> None:
    """Podwójne rozszerzenie / podmieniona zawartość: `.jpg` z treścią, która
    nie jest obrazem, nie może przejść tylko dlatego, że nazwa pliku wygląda
    poprawnie. `validate_cover_image` sprawdza tylko rozszerzenie i rozmiar —
    to `forms.ImageField` (przez Pillow) odrzuca faktycznie uszkodzony/nie-
    obrazowy plik. Test pilnuje, żeby ta druga warstwa obrony nie zniknęła
    (np. przy podmianie widgetu/pola w przyszłości)."""
    fake_jpg = SimpleUploadedFile("cover.jpg", b"<?php echo 'pwn'; ?>", content_type="image/jpeg")
    form = build_form(author, files={"cover_image": fake_jpg})

    assert not form.is_valid()
    assert "cover_image" in form.errors


def test_blad_na_innym_polu_ostrzega_ze_obraz_trzeba_wybrac_jeszcze_raz(author: Any) -> None:
    """Przeglądarka czyści `<input type="file">` przy każdym ponownym pokazaniu
    formularza — jeśli walidacja odrzuci formularz z JAKIEGOKOLWIEK innego
    powodu, wybrany obraz i tak zniknie przy zapisie. Bez tego ostrzeżenia
    redaktor poprawia zgłoszony błąd, zapisuje ponownie i dostaje post bez
    okładki, nie wiedząc dlaczego (tak zniknął obraz na poście „agata")."""
    form = build_form(author, title="", files={"cover_image": _valid_jpeg()})

    assert not form.is_valid()
    message = " ".join(form.errors["cover_image"])
    assert "wybierz go jeszcze raz" in message


def test_brak_alt_przy_publikacji_ostrzega_ze_obraz_trzeba_wybrac_jeszcze_raz(author: Any) -> None:
    """Dokładna sekwencja, która zgubiła okładkę na poście „agata": obraz
    przesłany, `cover_image_alt` puste, status od razu ustawiony na
    „Opublikowany"."""
    form = build_form(
        author,
        status=PostStatus.PUBLISHED,
        cover_image_alt="",
        files={"cover_image": _valid_jpeg()},
    )

    assert not form.is_valid()
    assert "missing_cover_image_alt" in [e.code for e in form.errors.as_data()["cover_image_alt"]]
    message = " ".join(form.errors["cover_image"])
    assert "wybierz go jeszcze raz" in message


def test_poprawny_formularz_z_obrazem_nie_dostaje_ostrzezenia(author: Any) -> None:
    """Gdy formularz jest poprawny, obraz zapisuje się normalnie — bez
    fałszywego alarmu o utracie pliku."""
    form = build_form(
        author, cover_image_alt="Nalewka z pigwy w słoiku.", files={"cover_image": _valid_jpeg()}
    )

    assert form.is_valid(), form.errors

    post = form.save()
    assert post.cover_image.name
