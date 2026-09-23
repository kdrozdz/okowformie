"""Serializer publicznego, read-only API plików do pobrania
(`/api/v1/{lang}/downloads/`).

Ręczny serializer korzystający z już przetestowanej, wolnej od N+1 metody
`translations_by_language()` (`downloads/managers.py`,
`.claude/rules/performance.md`) — wzorzec `blog.serializers.PostListSerializer`.
"""

from rest_framework import serializers

from core.api import absolute_media_url

from .models import Download, DownloadTranslation


class DownloadListSerializer(serializers.Serializer):
    """Pola listy plików do pobrania."""

    title = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()
    file = serializers.SerializerMethodField()
    order = serializers.IntegerField()

    def _translation(self, download: Download) -> DownloadTranslation:
        # Queryset (`DownloadQuerySet.published`) gwarantuje, że tłumaczenie
        # w żądanym języku istnieje i jest opublikowane — `KeyError` tutaj
        # oznaczałby błąd querysetu, nie brakujące dane.
        return download.translations_by_language()[self.context["language_code"]]

    def get_title(self, download: Download) -> str:
        return self._translation(download).title

    def get_description(self, download: Download) -> str:
        return self._translation(download).description

    def get_file(self, download: Download) -> str:
        # `file` jest wymagane na poziomie modelu (`Download.file`, bez
        # `blank=True`), w przeciwieństwie do opcjonalnych obrazów w
        # `blog`/`about` — nie ma tu gałęzi `None`.
        return absolute_media_url(download.file.url)
