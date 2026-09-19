from django.apps import AppConfig


class BlogConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "blog"
    verbose_name = "Blog"

    def ready(self) -> None:
        # Rejestracja systemowych checków (`manage.py check`).
        from . import checks  # noqa: F401
