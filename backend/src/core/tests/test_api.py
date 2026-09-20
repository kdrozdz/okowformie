"""`absolute_media_url` — budowanie publicznego URL-a obrazu, nie z `Host` żądania.

Pełny scenariusz (pole `photo`/`cover_image` w prawdziwym serializerze) jest
już pokryty przez `about/tests/test_api_about.py` i
`blog/tests/test_api_posts.py` — tu bezpośrednie testy samej funkcji,
włącznie z gałęzią, której tamte testy nie mogą łatwo wywołać: storage
zwracający już absolutny URL (przyszły S3, `.claude/rules/scope.md`).
"""

from django.test import override_settings

from core.api import absolute_media_url


@override_settings(SITE_URL="http://localhost:8000")
def test_sciezka_wzgledna_jest_doklejana_do_site_url() -> None:
    assert absolute_media_url("/media/about/photo/x.jpg") == "http://localhost:8000/media/about/photo/x.jpg"


@override_settings(SITE_URL="http://localhost:8000/")
def test_koncowy_slash_w_site_url_nie_daje_podwojnego_slasha() -> None:
    assert absolute_media_url("/media/x.jpg") == "http://localhost:8000/media/x.jpg"


@override_settings(SITE_URL="http://localhost:8000")
def test_juz_absolutny_url_wraca_bez_zmian() -> None:
    # Storage typu S3 (`django-storages`) zwraca z `.url` gotowy absolutny
    # URL do własnej domeny (bucket/CDN) — SITE_URL byłby tu błędny.
    s3_url = "https://bucket.s3.amazonaws.com/media/about/photo/x.jpg"
    assert absolute_media_url(s3_url) == s3_url
