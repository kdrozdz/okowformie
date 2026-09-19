"""Wspólne fixture'y testów bloga."""

from collections.abc import Callable
from typing import Any

import pytest
from django.contrib.auth import get_user_model

from blog.constants import Language, PostStatus
from blog.models import Post, PostTranslation


@pytest.fixture
def author(db: Any) -> Any:
    return get_user_model().objects.create_user(username="redaktorka", password="haslo-testowe-123")


@pytest.fixture
def make_post(author: Any) -> Callable[..., Post]:
    """Twórz post z dowolnym zestawem tłumaczeń.

    Przykład: `make_post(pl={"title": "Tytuł"}, en=None)` — post bez wersji
    angielskiej.
    """

    def _make(**languages: dict[str, Any] | None) -> Post:
        post = Post.objects.create(author=author)
        for language_code, values in languages.items():
            if values is None:
                continue
            defaults: dict[str, Any] = {
                "title": f"Tytuł {language_code}",
                "excerpt": f"Zajawka {language_code}",
                "content": "<p>Treść</p>",
                "status": PostStatus.DRAFT,
            }
            PostTranslation.objects.create(
                master=post, language_code=language_code, **(defaults | values)
            )
        return post

    return _make


@pytest.fixture
def published_post(make_post: Callable[..., Post]) -> Post:
    return make_post(
        pl={"title": "Nalewka z pigwy", "status": PostStatus.PUBLISHED},
        en={"title": "Quince liqueur", "status": PostStatus.PUBLISHED},
    )


__all__ = ["Language", "author", "make_post", "published_post"]
