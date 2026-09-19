"""Generowanie slugów — część bez bazy danych."""

from blog.slugs import FALLBACK_SLUG, build_unique_slug, slugify_pl

NOTHING_TAKEN = {"is_taken": lambda candidate: False}


def test_polskie_znaki_nie_gina() -> None:
    # Gołe `slugify()` Django zwróciłoby tu `zoty-myn` — `ł` nie ma
    # dekompozycji NFKD i znika bez śladu.
    assert slugify_pl("Żółty młyn") == "zolty-mlyn"


def test_transliteruje_wszystkie_polskie_diakrytyki() -> None:
    assert slugify_pl("ĄĆĘŁŃÓŚŹŻ ąćęłńóśźż") == "acelnoszz-acelnoszz"


def test_slug_z_tytulu() -> None:
    assert build_unique_slug("Nalewka z pigwy", max_length=220, **NOTHING_TAKEN) == (
        "nalewka-z-pigwy"
    )


def test_tytul_bez_znakow_slugowalnych_dostaje_fallback() -> None:
    assert build_unique_slug("!!! ???", max_length=220, **NOTHING_TAKEN) == FALLBACK_SLUG


def test_zajety_slug_dostaje_kolejny_numer() -> None:
    taken = {"nalewka", "nalewka-2"}

    result = build_unique_slug("Nalewka", is_taken=taken.__contains__, max_length=220)

    assert result == "nalewka-3"


def test_slug_nie_przekracza_max_length_takze_z_sufiksem() -> None:
    taken = {"a" * 10}

    result = build_unique_slug("a" * 50, is_taken=taken.__contains__, max_length=10)

    assert len(result) <= 10
    assert result == "aaaaaaaa-2"
