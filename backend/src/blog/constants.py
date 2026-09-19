"""Stałe domenowe bloga: języki treści i stany publikacji.

Osobny moduł, bo te wartości są potrzebne w modelach, formularzach, adminie
i systemowym checku — import z `models.py` wiązałby te miejsca z warstwą ORM
bez powodu.
"""

from django.db import models


class Language(models.TextChoices):
    """Języki, w których istnieje treść bloga.

    Lustro `settings.LANGUAGES` — to stamtąd `django-parler` bierze `choices`
    dla `PostTranslation.language_code`. Zgodność obu list pilnuje
    `blog.checks.check_languages_match_settings`.
    """

    PL = "pl", "polski"
    EN = "en", "angielski"


class PostStatus(models.TextChoices):
    """Stan publikacji — **per tłumaczenie**, nie per post.

    PL może być `PUBLISHED`, gdy EN jest wciąż `DRAFT`
    (`docs/decisions/2026-09-19-model-post.md`).
    """

    DRAFT = "draft", "Szkic"
    PUBLISHED = "published", "Opublikowany"
    ARCHIVED = "archived", "Zarchiwizowany"


#: Jedyny status widoczny publicznie. Wszystko inne (`draft`, `archived`)
#: jest odfiltrowywane w querysecie, nigdy w serializerze ani na froncie
#: (`.claude/rules/security.md`).
PUBLIC_STATUS = PostStatus.PUBLISHED

#: Maksymalna długość `meta_title` zalecana przez wyszukiwarki.
META_TITLE_MAX_LENGTH = 60

#: Zalecany przedział długości `meta_description` (poniżej — marnujemy
#: miejsce w SERP-ie, powyżej — Google ucina opis w połowie zdania).
META_DESCRIPTION_MIN_LENGTH = 150
META_DESCRIPTION_MAX_LENGTH = 160
