"""Testy `branding.icons.social_platform_icon_html`."""

from branding.icons import social_platform_icon_html
from branding.models import SocialPlatform


def test_znana_platforma_zwraca_znacznik_svg() -> None:
    html = social_platform_icon_html(SocialPlatform.LINKEDIN)

    assert "<svg" in html


def test_nieznana_platforma_zwraca_pusty_string_bez_wyjatku() -> None:
    html = social_platform_icon_html("tiktok")

    assert html == ""
