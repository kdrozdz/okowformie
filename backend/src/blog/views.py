"""Publiczne, read-only widoki API bloga (`GET /api/v1/{lang}/posts/...`).

Tylko odczyt w fazie 1 (`.claude/rules/security.md`) — brak `create`/
`update`/`delete` tu nie jest przeoczeniem.
"""

from typing import Any

from django.http import Http404
from rest_framework import generics
from rest_framework.request import Request
from rest_framework.response import Response

from .constants import Language
from .models import Post
from .pagination import PostPagination
from .serializers import PostDetailSerializer, PostListSerializer
from .throttling import PostsAnonRateThrottle

#: Wspólny `Cache-Control` dla obu publicznych endpointów. Dostawca CDN
#: nierozstrzygnięty (poza zakresem `docs/tasks/8-publiczne-api.md`), ale
#: sam nagłówek od niego nie zależy (`.claude/rules/performance.md`).
_CACHE_CONTROL = "public, max-age=60"


class LanguageURLKwargMixin:
    """Waliduje `lang` z URL-a — nieobsługiwany kod języka to 404, nie 400.

    Kontrakt traktuje zły `lang` tak samo jak nieistniejący zasób
    (`docs/tasks/8-publiczne-api.md`).
    """

    kwargs: dict[str, Any]

    def get_language_code(self) -> str:
        language_code = self.kwargs["lang"]
        if language_code not in Language.values:
            raise Http404(f"Unsupported language: {language_code!r}.")
        return language_code


class CacheControlMixin:
    """Dokłada `Cache-Control` do udanych odpowiedzi.

    Błędy (404/429) nie są cache'owane — nagłówek dotyczy tylko treści,
    którą warto trzymać przed API (`.claude/rules/performance.md`).
    """

    def finalize_response(
        self, request: Request, response: Response, *args: Any, **kwargs: Any
    ) -> Response:
        response = super().finalize_response(request, response, *args, **kwargs)  # type: ignore[misc]
        if response.status_code == 200:
            response["Cache-Control"] = _CACHE_CONTROL
        return response


class PostListView(CacheControlMixin, LanguageURLKwargMixin, generics.ListAPIView):
    """`GET /api/v1/{lang}/posts/?page={n}` — lista opublikowanych postów."""

    serializer_class = PostListSerializer
    pagination_class = PostPagination
    throttle_classes = (PostsAnonRateThrottle,)

    def get_queryset(self) -> Any:
        return Post.objects.published(self.get_language_code())

    def get_serializer_context(self) -> dict[str, Any]:
        context = super().get_serializer_context()
        context["language_code"] = self.get_language_code()
        return context


class PostDetailView(CacheControlMixin, LanguageURLKwargMixin, generics.RetrieveAPIView):
    """`GET /api/v1/{lang}/posts/{slug}/` — szczegół opublikowanego posta."""

    serializer_class = PostDetailSerializer
    throttle_classes = (PostsAnonRateThrottle,)

    def get_object(self) -> Post:
        try:
            return Post.objects.get_published(self.get_language_code(), self.kwargs["slug"])
        except Post.DoesNotExist as exc:
            raise Http404 from exc

    def get_serializer_context(self) -> dict[str, Any]:
        context = super().get_serializer_context()
        context["language_code"] = self.get_language_code()
        return context
