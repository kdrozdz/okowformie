"""Serializer publicznego, read-only API strony „O mnie" (`/api/v1/{lang}/about/`).

Wzorowany 1:1 na `blog.serializers.PostDetailSerializer`
(`docs/decisions/2026-09-19-model-about-me.md`): ręczny serializer korzystający
z już przetestowanej, wolnej od N+1 metody `translations_by_language()`
(`about/managers.py`, `.claude/rules/performance.md`), zamiast konfigurować
`django-parler-rest` pod inny kształt pól niż domyślny.
"""

from datetime import datetime

from rest_framework import serializers

from core.constants import PUBLIC_STATUS

from .models import AboutMe, AboutMeTranslation, Certificate


class CertificateSerializer(serializers.Serializer):
    """Certyfikaty wypisane w kolejności `Certificate.Meta.ordering` (`order`, `id`).

    Zawsze wszystkie — bez własnego stanu draft/published
    (`docs/decisions/2026-09-19-model-about-me.md`): widoczność wiąże się z
    publikacją strony `AboutMe` w danym języku, nie z pojedynczym certyfikatem.
    """

    name = serializers.CharField()
    issuer = serializers.CharField()
    issued_year = serializers.IntegerField()
    image = serializers.SerializerMethodField()

    def get_image(self, certificate: Certificate) -> str | None:
        if not certificate.image:
            return None
        request = self.context.get("request")
        url = certificate.image.url
        return request.build_absolute_uri(url) if request is not None else url


class AboutDetailSerializer(serializers.Serializer):
    """Pojedynczy obiekt (nie lista) — strona „O mnie" jest singletonem."""

    full_name = serializers.SerializerMethodField()
    headline = serializers.SerializerMethodField()
    bio = serializers.SerializerMethodField()
    photo = serializers.SerializerMethodField()
    photo_alt = serializers.SerializerMethodField()
    meta_title = serializers.SerializerMethodField()
    meta_description = serializers.SerializerMethodField()
    updated_at = serializers.SerializerMethodField()
    available_translations = serializers.SerializerMethodField()
    certificates = serializers.SerializerMethodField()

    def _translation(self, about: AboutMe) -> AboutMeTranslation:
        # Queryset (`AboutMeManager.get_published`) gwarantuje, że
        # tłumaczenie w żądanym języku istnieje i jest opublikowane —
        # `KeyError` tutaj oznaczałby błąd managera, nie brakujące dane.
        return about.translations_by_language()[self.context["language_code"]]

    def get_full_name(self, about: AboutMe) -> str:
        return about.full_name

    def get_headline(self, about: AboutMe) -> str:
        return self._translation(about).headline

    def get_bio(self, about: AboutMe) -> str:
        # Zawsze `bio_html` (sanityzowane), nigdy surowe `bio`
        # (`.claude/rules/security.md`).
        return self._translation(about).bio_html

    def get_photo(self, about: AboutMe) -> str | None:
        if not about.photo:
            return None
        request = self.context.get("request")
        url = about.photo.url
        return request.build_absolute_uri(url) if request is not None else url

    def get_photo_alt(self, about: AboutMe) -> str:
        return self._translation(about).photo_alt

    def get_meta_title(self, about: AboutMe) -> str:
        return self._translation(about).seo_title

    def get_meta_description(self, about: AboutMe) -> str:
        return self._translation(about).seo_description

    def get_updated_at(self, about: AboutMe) -> datetime:
        return self._translation(about).updated_at

    def get_available_translations(self, about: AboutMe) -> list[dict[str, str]]:
        """Tylko opublikowane wersje — szkic w innym języku nie ma wyciekać.

        Bez `slug` (w przeciwieństwie do `blog.serializers`): strona „O mnie"
        jest singletonem pod stałym adresem, nie ma własnego routingu po slugu.
        """
        translations = about.translations_by_language()
        return [
            {"language": language_code}
            for language_code, translation in sorted(translations.items())
            if translation.status == PUBLIC_STATUS
        ]

    def get_certificates(self, about: AboutMe) -> list[dict[str, object]]:
        certificates = CertificateSerializer(
            about.certificates.all(), many=True, context=self.context
        )
        return certificates.data
