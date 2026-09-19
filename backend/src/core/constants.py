"""Stałe domenowo neutralne, współdzielone między `blog` i `about`.

Wydzielone z `blog.constants` (`docs/decisions/2026-09-19-model-about-me.md`):
`Language` i stan publikacji były pomyślane jako pojęcia bloga, ale strona
„O mnie" (`about`) potrzebuje dokładnie tych samych pojęć — ten sam cykl
`draft -> published -> archived`, per język, i te same kody języków. Dwa
niezależne źródła prawdy o tym samym konstrukcie wymagałyby ręcznej
synchronizacji przy każdej zmianie (np. dojściu trzeciego języka), więc
`core` (bez modeli) jest wspólnym miejscem, od którego obie domeny treściowe
zależą, zamiast zależeć jedna od drugiej.

`blog.constants` re-eksportuje stąd te same nazwy, żeby nie zmieniać
istniejącego importu w `blog/` — zero zmiany zachowania, zero nowej migracji.
"""

from django.db import models


class Language(models.TextChoices):
    """Języki, w których istnieje treść serwisu.

    Lustro `settings.LANGUAGES` — to stamtąd `django-parler` bierze `choices`
    dla pól `language_code`. Zgodność obu list pilnuje
    `blog.checks.check_languages_match_settings`.
    """

    PL = "pl", "polski"
    EN = "en", "angielski"


class PublicationStatus(models.TextChoices):
    """Stan publikacji treści — **per tłumaczenie**, nie per rekord wspólny.

    PL może być `PUBLISHED`, gdy EN jest wciąż `DRAFT`
    (`docs/decisions/2026-09-19-model-post.md`).
    """

    DRAFT = "draft", "Szkic"
    PUBLISHED = "published", "Opublikowany"
    ARCHIVED = "archived", "Zarchiwizowany"


#: Jedyny status widoczny publicznie. Wszystko inne (`draft`, `archived`)
#: jest odfiltrowywane w querysecie, nigdy w serializerze ani na froncie
#: (`.claude/rules/security.md`).
PUBLIC_STATUS = PublicationStatus.PUBLISHED

#: Maksymalna długość `meta_title` zalecana przez wyszukiwarki.
META_TITLE_MAX_LENGTH = 60

#: Zalecany przedział długości `meta_description` (poniżej — marnujemy
#: miejsce w SERP-ie, powyżej — Google ucina opis w połowie zdania).
META_DESCRIPTION_MIN_LENGTH = 150
META_DESCRIPTION_MAX_LENGTH = 160
