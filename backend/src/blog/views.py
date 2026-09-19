"""Publiczne, read-only widoki API bloga (`GET /api/v1/{lang}/posts/...`).

Tylko odczyt w fazie 1 (`.claude/rules/security.md`) — brak `create`/
`update`/`delete` tu nie jest przeoczeniem.

`LanguageURLKwargMixin` i `CacheControlMixin` mieszkają w `core.api`
(`docs/decisions/2026-09-19-model-about-me.md`) — `about` korzysta z nich w
ten sam sposób, więc nie ma powodu trzymać dwóch kopii tej samej logiki.
"""

from typing import Any

from django.http import Http404
from rest_framework import generics

from core.api import CacheControlMixin, LanguageURLKwargMixin

from .models import Post
from .pagination import PostPagination
from .serializers import PostDetailSerializer, PostListSerializer
from .throttling import PostsAnonRateThrottle


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
