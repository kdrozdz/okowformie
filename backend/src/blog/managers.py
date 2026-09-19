"""Querysety bloga.

Filtrowanie po statusie żyje tutaj, w warstwie querysetu — nigdy w
serializerze ani na froncie (`.claude/rules/security.md`). Dzięki temu
„niepublikowane treści nie wyciekają" jest własnością zapytania, a nie
dyscypliny każdego kolejnego widoku.
"""

from typing import TYPE_CHECKING, Any

from django.db import models
from parler.managers import TranslatableManager, TranslatableQuerySet

from .constants import PUBLIC_STATUS

if TYPE_CHECKING:
    # `models` importuje ten moduł, więc w drugą stronę tylko dla typów.
    from .models import Post

    # `django-parler` nie ma `py.typed`, więc dla mypy jego menedżer jest
    # `Any` — a wtedy wtyczka `django-stubs` nie potrafi rozwiązać
    # `Post._default_manager` i wywraca się na relacji odwrotnej
    # `User.posts`. Dla typów udajemy zwykły `Manager[Post]`; w runtime
    # dziedziczymy po prawdziwym menedżerze parlera.
    _PostManagerBase = models.Manager["Post"]
else:
    _PostManagerBase = TranslatableManager


class PostQuerySet(TranslatableQuerySet):
    """Queryset mastera. Wszystkie metody publiczne zawężają do `published`."""

    def _translated_as(self, language_code: str, **conditions: Any) -> PostQuerySet:
        """Posty mające tłumaczenie spełniające **wszystkie** warunki naraz.

        Kluczowe, że warunki lecą jednym `filter()` (tak działa parlerowe
        `translated()`): przy wielowartościowej relacji osobne `filter()`
        dokładałyby osobne JOIN-y i post z opublikowanym PL dopasowałby się
        do slugu z EN. To dokładnie ten błąd, który ma wychwycić test
        „slug z jednego języka w routingu drugiego".
        """
        queryset: PostQuerySet = self.translated(language_code, **conditions)
        return (
            queryset.language(language_code)
            .select_related("author")
            # Wszystkie tłumaczenia, nie tylko bieżące: strona posta i tak
            # potrzebuje listy dostępnych wersji pod przełącznik języka i
            # `hreflang` (`docs/decisions/2026-09-19-model-post.md`). Przy
            # dwóch wierszach na post to tańsze niż dodatkowe zapytanie.
            .prefetch_related("translations")
        )

    def published(self, language_code: str) -> PostQuerySet:
        """Posty z opublikowanym tłumaczeniem w danym języku.

        `draft` i `archived` odpadają tu, a nie w warstwie prezentacji.
        """
        return self._translated_as(language_code, status=PUBLIC_STATUS)

    def published_by_slug(self, language_code: str, slug: str) -> PostQuerySet:
        """Zawęź do jednego opublikowanego posta po slugu **w tym języku**."""
        return self._translated_as(language_code, status=PUBLIC_STATUS, slug=slug)


class PostManager(_PostManagerBase):
    """Domyślny manager `Post` — parlerowy, wzbogacony o filtry publikacji."""

    def get_queryset(self) -> PostQuerySet:
        # Ciało jak w `models.Manager.get_queryset()`, tylko z naszą klasą
        # querysetu. Nie używamy `from_queryset()`, bo generowana dynamicznie
        # klasa bazowa jest nierozwiązywalna statycznie.
        return PostQuerySet(model=self.model, using=self._db, hints=self._hints)  # type: ignore[attr-defined]

    def published(self, language_code: str) -> PostQuerySet:
        return self.get_queryset().published(language_code)

    def get_published(self, language_code: str, slug: str) -> Post:
        """Pojedynczy opublikowany post albo `Post.DoesNotExist` (czyli 404).

        Świadomie bez fallbacku na inny język: żądanie `/en/<slug>` dla
        posta, który ma tylko PL, ma być 404, a nie cichym podaniem polskiej
        treści pod angielskim `hreflang`.
        """
        return self.get_queryset().published_by_slug(language_code, slug).get()
