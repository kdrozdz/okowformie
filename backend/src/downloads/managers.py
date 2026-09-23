"""Queryset/manager plików do pobrania.

Filtrowanie po statusie żyje tutaj, w warstwie querysetu — nigdy w
serializerze ani na froncie (`.claude/rules/security.md`). Wzorzec
`blog.managers.PostQuerySet`/`PostManager`, bez odpowiednika
`published_by_slug`: lista plików do pobrania nie ma detalu po slugu.
"""

from typing import TYPE_CHECKING

from django.db import models
from parler.managers import TranslatableManager, TranslatableQuerySet

from core.constants import PUBLIC_STATUS

if TYPE_CHECKING:
    # Import potrzebny wyłącznie dla mypy (forward ref w `Manager["Download"]`
    # niżej) — ruff/pyflakes nie liczy tego jako użycie, bo `Download`
    # pojawia się tylko jako string wewnątrz subskrypcji, nie w adnotacji.
    # `django-parler` nie ma `py.typed`, więc dla mypy jego menedżer jest
    # `Any` — ten sam obchód co `blog.managers._PostManagerBase`.
    from .models import Download  # noqa: F401

    _DownloadManagerBase = models.Manager["Download"]
else:
    _DownloadManagerBase = TranslatableManager


class DownloadQuerySet(TranslatableQuerySet):
    """Queryset mastera. `published()` zawęża do opublikowanego tłumaczenia."""

    def published(self, language_code: str) -> DownloadQuerySet:
        """Pliki z opublikowanym tłumaczeniem w danym języku, posortowane po `order`.

        `draft` i `archived` odpadają tu, a nie w warstwie prezentacji.
        """
        queryset: DownloadQuerySet = self.translated(language_code, status=PUBLIC_STATUS)
        return (
            queryset.language(language_code)
            .prefetch_related("translations")
            .order_by("order", "id")
        )


class DownloadManager(_DownloadManagerBase):
    """Domyślny manager `Download` — parlerowy, wzbogacony o `published`."""

    def get_queryset(self) -> DownloadQuerySet:
        # Ciało jak w `models.Manager.get_queryset()`, tylko z naszą klasą
        # querysetu — ten sam wzorzec co `blog.managers.PostManager`.
        return DownloadQuerySet(model=self.model, using=self._db, hints=self._hints)  # type: ignore[attr-defined]

    def published(self, language_code: str) -> DownloadQuerySet:
        return self.get_queryset().published(language_code)
