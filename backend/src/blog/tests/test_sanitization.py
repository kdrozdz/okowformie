"""Sanityzacja HTML — twarde wymaganie z `.claude/rules/security.md`."""

import pytest

from blog.sanitization import sanitize_post_html


@pytest.mark.parametrize("empty", ["", None])
def test_pusta_tresc_zwraca_pusty_string(empty: str | None) -> None:
    assert sanitize_post_html(empty) == ""


def test_usuwa_tag_script() -> None:
    result = sanitize_post_html('<p>Przepis</p><script>alert("xss")</script>')

    assert "<script" not in result
    assert "alert" not in result
    assert "<p>Przepis</p>" in result


def test_usuwa_handler_onerror() -> None:
    result = sanitize_post_html('<img src="okladka.jpg" onerror="alert(1)" alt="Okładka">')

    assert "onerror" not in result
    assert "alert" not in result
    assert 'alt="Okładka"' in result


def test_usuwa_dowolny_handler_zdarzenia() -> None:
    result = sanitize_post_html('<p onclick="steal()" onmouseover="steal()">Tekst</p>')

    assert "onclick" not in result
    assert "onmouseover" not in result
    assert "Tekst" in result


def test_usuwa_link_ze_schematem_javascript() -> None:
    result = sanitize_post_html('<a href="javascript:alert(1)">kliknij</a>')

    assert "javascript" not in result
    assert "kliknij" in result


def test_usuwa_obraz_z_data_uri() -> None:
    result = sanitize_post_html('<img src="data:text/html;base64,PHNjcmlwdD4=" alt="x">')

    assert "data:" not in result


def test_usuwa_iframe() -> None:
    result = sanitize_post_html('<iframe src="https://example.com"></iframe>')

    assert "iframe" not in result


def test_usuwa_style_i_class() -> None:
    result = sanitize_post_html('<p style="position:fixed" class="overlay">Tekst</p>')

    assert "style=" not in result
    assert "class=" not in result
    assert "Tekst" in result


def test_usuwa_h1_bo_naglowek_strony_jest_jeden() -> None:
    result = sanitize_post_html("<h1>Drugi H1</h1><h2>Podtytuł</h2>")

    assert "<h1>" not in result
    assert "<h2>Podtytuł</h2>" in result


def test_zachowuje_formatowanie_redakcyjne() -> None:
    source = (
        "<h2>Składniki</h2>"
        "<ul><li><strong>Pigwa</strong> — 1 kg</li><li><em>Cukier</em></li></ul>"
        "<blockquote>Cytat</blockquote>"
        '<p>Więcej w <a href="https://example.com">notatce</a>.</p>'
    )

    result = sanitize_post_html(source)

    for fragment in ("<h2>Składniki</h2>", "<strong>Pigwa</strong>", "<em>Cukier</em>"):
        assert fragment in result
    assert "<blockquote>Cytat</blockquote>" in result
    assert 'href="https://example.com"' in result


def test_dokleja_rel_do_linkow() -> None:
    result = sanitize_post_html('<a href="https://example.com">link</a>')

    assert 'rel="noopener noreferrer"' in result
