"""Serializery publicznego, read-only API bloga (`/api/v1/{lang}/posts/`).

Ręczny serializer na `Post` + `Post.translations_by_language()` zamiast
`django-parler-rest`: kontrakt (`docs/tasks/8-publiczne-api.md`) ma inne
nazwy i kształt pól niż domyślny, płaski format parlera (`content` ma być
zawsze `content_html`, nigdy surowe pole; autor to sama nazwa wyświetlana,
nie cały obiekt konta) — i tak trzeba by nadpisać większość generowanych
pól, więc jeden jawny serializer korzystający z już przetestowanej, wolnej
od N+1 metody `translations_by_language()` (`blog/managers.py`,
`.claude/rules/performance.md`) jest prostszy niż konfigurowanie biblioteki
pod wyjątki.
"""

from datetime import datetime

from rest_framework import serializers

from core.api import absolute_media_url

from .constants import PostStatus
from .models import Post, PostTranslation

#: Fallback, gdy autor nie ma uzupełnionego imienia i nazwiska na koncie.
#: Publiczne API pokazuje wyłącznie nazwę wyświetlaną — nigdy `username`
#: ani inne dane konta (`docs/tasks/8-publiczne-api.md`) — więc pusty
#: `get_full_name()` nie może cicho spaść na login.
_DEFAULT_AUTHOR_DISPLAY_NAME = "Redakcja"


class PostListSerializer(serializers.Serializer):
    """Pola listy — bez pełnej treści (`.claude/rules/performance.md`)."""

    slug = serializers.SerializerMethodField()
    title = serializers.SerializerMethodField()
    excerpt = serializers.SerializerMethodField()
    cover_image = serializers.SerializerMethodField()
    cover_image_alt = serializers.SerializerMethodField()
    author = serializers.SerializerMethodField()
    published_at = serializers.SerializerMethodField()

    def _translation(self, post: Post) -> PostTranslation:
        # Queryset (`PostQuerySet.published`/`get_published`) gwarantuje, że
        # tłumaczenie w żądanym języku istnieje i jest opublikowane —
        # `KeyError` tutaj oznaczałby błąd querysetu, nie brakujące dane.
        return post.translations_by_language()[self.context["language_code"]]

    def get_slug(self, post: Post) -> str:
        return self._translation(post).slug

    def get_title(self, post: Post) -> str:
        return self._translation(post).title

    def get_excerpt(self, post: Post) -> str:
        return self._translation(post).excerpt

    def get_cover_image(self, post: Post) -> str | None:
        if not post.cover_image:
            return None
        return absolute_media_url(post.cover_image.url)

    def get_cover_image_alt(self, post: Post) -> str:
        return self._translation(post).cover_image_alt

    def get_author(self, post: Post) -> str:
        return post.author.get_full_name() or _DEFAULT_AUTHOR_DISPLAY_NAME

    def get_published_at(self, post: Post) -> datetime | None:
        return self._translation(post).published_at


class PostDetailSerializer(PostListSerializer):
    """Jak lista, plus treść i metadane szczegółu posta."""

    content = serializers.SerializerMethodField()
    meta_title = serializers.SerializerMethodField()
    meta_description = serializers.SerializerMethodField()
    updated_at = serializers.SerializerMethodField()
    available_translations = serializers.SerializerMethodField()

    def get_content(self, post: Post) -> str:
        # Zawsze `content_html` (sanityzowany), nigdy surowe `content`
        # (`.claude/rules/security.md`).
        return self._translation(post).content_html

    def get_meta_title(self, post: Post) -> str:
        # `seo_title`, nie surowe `meta_title` — pole bywa puste (panel
        # redakcyjny zachęca do zostawienia go pustym), a `.claude/rules/seo.md`
        # zabrania pustego taga w HTML. Fallback na tytuł jest wbudowany
        # w model (`PostTranslation.seo_title`), nie duplikujemy go tutaj.
        return self._translation(post).seo_title

    def get_meta_description(self, post: Post) -> str:
        return self._translation(post).seo_description

    def get_updated_at(self, post: Post) -> datetime:
        return self._translation(post).updated_at

    def get_available_translations(self, post: Post) -> list[dict[str, str]]:
        """Tylko opublikowane wersje — szkic w innym języku nie ma wyciekać."""
        translations = post.translations_by_language()
        return [
            {"language": language_code, "slug": translation.slug}
            for language_code, translation in sorted(translations.items())
            if translation.status == PostStatus.PUBLISHED
        ]
