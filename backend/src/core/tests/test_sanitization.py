"""Sanityzacja HTML współdzielona przez `blog` i `about` (`.claude/rules/security.md`).

Pełny zestaw wektorów XSS jest już przetestowany pośrednio przez
`blog/tests/test_sanitization.py` (re-eksport pod `sanitize_post_html`
wywołuje dokładnie tę samą funkcję) — tu tylko bezpośredni smoke test
kanonicznej implementacji, żeby `core` miał własne, niezależne od `blog`
pokrycie.
"""

import pytest

from core.sanitization import sanitize_html


@pytest.mark.parametrize("empty", ["", None])
def test_pusta_tresc_zwraca_pusty_string(empty: str | None) -> None:
    assert sanitize_html(empty) == ""


def test_usuwa_tag_script() -> None:
    result = sanitize_html('<p>Tekst</p><script>alert("xss")</script>')

    assert "<script" not in result
    assert "<p>Tekst</p>" in result


def test_usuwa_handler_zdarzenia() -> None:
    result = sanitize_html('<img src="x.jpg" onerror="alert(1)" alt="Opis">')

    assert "onerror" not in result
    assert 'alt="Opis"' in result


def test_dokleja_rel_do_linkow() -> None:
    result = sanitize_html('<a href="https://example.com">link</a>')

    assert 'rel="noopener noreferrer"' in result
