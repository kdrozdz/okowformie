"""Serializer publicznego, read-only API brandingu strony (`/api/v1/branding/`).

Wzorowany na `about.serializers.AboutDetailSerializer`
(`docs/tasks/11-branding-header.md`): ręczny `serializers.Serializer` na
pojedynczym obiekcie (branding jest singletonem, jak `AboutMe`).
"""

from rest_framework import serializers

from core.api import absolute_media_url

from .models import SiteBranding


class SocialLinkSerializer(serializers.Serializer):
    """Linki wypisane w kolejności `SocialLink.Meta.ordering` (`order`, `id`)."""

    platform = serializers.CharField()
    url = serializers.URLField()


class SiteBrandingSerializer(serializers.Serializer):
    """Pojedynczy obiekt (nie lista) — branding strony jest singletonem."""

    logo = serializers.SerializerMethodField()
    social_links = serializers.SerializerMethodField()

    def get_logo(self, branding: SiteBranding) -> str | None:
        if not branding.logo:
            return None
        return absolute_media_url(branding.logo.url)

    def get_social_links(self, branding: SiteBranding) -> list[dict[str, str]]:
        if branding.pk is None:
            # Instancja nieutrwalona (pusty stan, panel jeszcze
            # nieskonfigurowany) — `branding.social_links` to menedżer
            # reverse-FK, `.all()` na nieutrwalonej instancji rzuciłby błąd
            # zamiast zwrócić pusty queryset.
            return []
        links = SocialLinkSerializer(branding.social_links.all(), many=True)
        return links.data
