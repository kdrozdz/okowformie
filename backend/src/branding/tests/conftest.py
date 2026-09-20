"""Wspólne fixture'y testów `branding`."""

from collections.abc import Callable
from typing import Any

import pytest

from branding.models import SiteBranding, SocialLink, SocialPlatform


@pytest.fixture
def make_branding(db: Any) -> Callable[..., SiteBranding]:
    """Twórz `SiteBranding`. Kolejne wywołania zwracają ten sam singleton
    (`SiteBranding.save()` wymusza `pk=1`), jak `about.tests.conftest.make_about`.
    """

    def _make(**overrides: Any) -> SiteBranding:
        branding, _ = SiteBranding.objects.get_or_create(pk=SiteBranding.SINGLETON_ID)
        if overrides:
            for field, value in overrides.items():
                setattr(branding, field, value)
            branding.save()
        return branding

    return _make


@pytest.fixture
def make_social_link(db: Any) -> Callable[..., SocialLink]:
    def _make(branding: SiteBranding, **overrides: Any) -> SocialLink:
        defaults: dict[str, Any] = {
            "platform": SocialPlatform.LINKEDIN,
            "url": "https://www.linkedin.com/in/example",
            "order": 0,
        }
        return SocialLink.objects.create(branding=branding, **(defaults | overrides))

    return _make
