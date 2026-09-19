"""Manager `AboutMe`.

`AboutMe` jest singletonem (`AboutMe.SINGLETON_ID`) — w przeciwieństwie do
`blog.managers.PostQuerySet`, który filtruje potencjalnie setki wierszy, tu
wystarcza jedna metoda na managerze: pobierz jedyny rekord i sprawdź
tłumaczenie w pamięci. Osobny custom queryset byłby przerostem dla jednego
wiersza (`.claude/rules/engineering-principles.md` — KISS).

Filtrowanie po statusie żyje tutaj, nie w serializerze ani na froncie
(`.claude/rules/security.md`).
"""

from typing import TYPE_CHECKING

from django.db import models
from parler.managers import TranslatableManager

from core.constants import PUBLIC_STATUS

if TYPE_CHECKING:
    from .models import AboutMe

    # `django-parler` nie ma `py.typed`, więc dla mypy jego menedżer jest
    # `Any` — analogiczny obejście jak w `blog/managers.py`
    # (`_PostManagerBase`), z tym samym uzasadnieniem.
    _AboutMeManagerBase = models.Manager["AboutMe"]
else:
    _AboutMeManagerBase = TranslatableManager


class AboutMeManager(_AboutMeManagerBase):
    """Manager singletona — dodaje `get_published`, resztę zostawia parlerowi."""

    def get_published(self, language_code: str) -> AboutMe:
        """Jedyny rekord `AboutMe`, jeśli ma opublikowane tłumaczenie w danym języku.

        Bez fallbacku na inny język, tak jak `blog.managers.PostManager.get_published`
        — brak opublikowanej wersji EN ma dać 404, a nie po cichu podać treść PL.
        `self.model.DoesNotExist` (czyli 404) także wtedy, gdy singleton w
        ogóle nie został jeszcze utworzony w panelu.
        """
        about = self.prefetch_related("translations", "certificates").get(
            pk=self.model.SINGLETON_ID
        )
        translation = about.translations_by_language().get(language_code)
        if translation is None or translation.status != PUBLIC_STATUS:
            raise self.model.DoesNotExist(
                f"No published translation for language {language_code!r}."
            )
        return about
