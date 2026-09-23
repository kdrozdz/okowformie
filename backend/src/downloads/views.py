"""Publiczny, read-only widok API plików do pobrania
(`GET /api/v1/{lang}/downloads/`).

Wzorowany na `blog.views.PostListView`: ten sam `core.api.LanguageURLKwargMixin`/
`CacheControlMixin`, throttling z osobnym scope (`downloads/throttling.py`).
Bez własnej klasy paginacji — domyślny `PAGE_SIZE` z globalnych ustawień DRF
(`REST_FRAMEWORK["PAGE_SIZE"]`) wystarcza: w przeciwieństwie do bloga, lista
plików do pobrania nie uzasadnia świadomie mniejszej strony
(`docs/tasks/16-pliki-do-pobrania.md`). Tylko odczyt w fazie 1
(`.claude/rules/security.md`) — brak `create`/`update`/`delete` tu nie jest
przeoczeniem.
"""

from typing import Any

from rest_framework import generics

from core.api import CacheControlMixin, LanguageURLKwargMixin

from .models import Download
from .serializers import DownloadListSerializer
from .throttling import DownloadsAnonRateThrottle


class DownloadListView(CacheControlMixin, LanguageURLKwargMixin, generics.ListAPIView):
    """`GET /api/v1/{lang}/downloads/?page={n}` — lista opublikowanych plików."""

    serializer_class = DownloadListSerializer
    throttle_classes = (DownloadsAnonRateThrottle,)

    def get_queryset(self) -> Any:
        return Download.objects.published(self.get_language_code())

    def get_serializer_context(self) -> dict[str, Any]:
        context = super().get_serializer_context()
        context["language_code"] = self.get_language_code()
        return context
