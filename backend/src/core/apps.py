from django.apps import AppConfig


class CoreConfig(AppConfig):
    """Aplikacja bez modeli: stałe i narzędzia współdzielone między domenami.

    `blog` i `about` importują stąd `Language`/`PublicationStatus`, sanityzację
    HTML i walidację uploadu obrazu, żeby nie zależeć jedna od drugiej
    (`docs/decisions/2026-09-19-model-about-me.md`,
    `.claude/rules/scope.md`: apps podzielone domenowo).
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "core"
    verbose_name = "Rdzeń"
