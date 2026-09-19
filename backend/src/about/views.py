"""Publiczny, read-only widok API strony „O mnie" (`GET /api/v1/{lang}/about/`).

Wzorowany 1:1 na `blog.views.PostDetailView`
(`docs/decisions/2026-09-19-model-about-me.md`): ten sam
`core.api.LanguageURLKwargMixin`/`CacheControlMixin`, throttling z osobnym
scope (`about/throttling.py`). Tylko odczyt w fazie 1
(`.claude/rules/security.md`) — brak `create`/`update`/`delete` tu nie jest
przeoczeniem.
"""

from typing import Any

from django.http import Http404
from rest_framework import generics

from core.api import CacheControlMixin, LanguageURLKwargMixin

from .models import AboutMe
from .serializers import AboutDetailSerializer
from .throttling import AboutAnonRateThrottle


class AboutDetailView(CacheControlMixin, LanguageURLKwargMixin, generics.RetrieveAPIView):
    """`GET /api/v1/{lang}/about/` — pojedynczy obiekt, nie lista.

    404, gdy singleton nie istnieje jeszcze w panelu albo nie ma opublikowanego
    tłumaczenia w żądanym języku (`about.managers.AboutMeManager.get_published`).
    """

    serializer_class = AboutDetailSerializer
    throttle_classes = (AboutAnonRateThrottle,)

    def get_object(self) -> AboutMe:
        try:
            return AboutMe.objects.get_published(self.get_language_code())
        except AboutMe.DoesNotExist as exc:
            raise Http404 from exc

    def get_serializer_context(self) -> dict[str, Any]:
        context = super().get_serializer_context()
        context["language_code"] = self.get_language_code()
        return context
