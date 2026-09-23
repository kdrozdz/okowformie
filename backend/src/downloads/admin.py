"""Panel redakcyjny plików do pobrania.

Kryterium akceptacji jak przy blogu/„O mnie": redaktor jest osobą
nietechniczną, bez developera (`.claude/rules/content-admin.md`). Kolumny
statusu per język są zwykłym tekstem, nie kolorowymi kropkami jak
`blog.admin.PostAdmin._status_badge` — jedna, prosta lista plików nie
uzasadnia tego samego nakładu (`docs/tasks/16-pliki-do-pobrania.md`).
"""

from django.contrib import admin
from django.db.models import QuerySet
from django.http import HttpRequest
from parler.admin import TranslatableAdmin

from core.constants import Language

from .models import Download


@admin.register(Download)
class DownloadAdmin(TranslatableAdmin):
    list_display = ("admin_title", "status_pl", "status_en", "order")
    list_filter = ("translations__status",)
    search_fields = ("translations__title",)
    ordering = ("order", "id")

    fieldsets = (
        (
            None,
            {
                "fields": ("file", "order"),
                "description": (
                    "Zakładki u góry przełączają wersję językową nazwy i opisu tego "
                    "samego pliku. Sam plik jest wspólny dla obu języków."
                ),
            },
        ),
        ("Nazwa i opis", {"fields": ("title", "description")}),
        ("Publikacja", {"fields": ("status", "published_at")}),
    )

    def get_queryset(self, request: HttpRequest) -> QuerySet[Download]:
        """Jedno zapytanie na wszystkie tłumaczenia, nie jedno na wiersz —
        analogiczne do `blog.admin.PostAdmin.get_queryset`
        (`.claude/rules/performance.md`).
        """
        return super().get_queryset(request).prefetch_related("translations")

    # --- Kolumny listy --------------------------------------------------

    @admin.display(description="Nazwa", ordering="translations__title")
    def admin_title(self, obj: Download) -> str:
        return obj.safe_translation_getter("title", any_language=True) or "(bez nazwy)"

    @admin.display(description="polski")
    def status_pl(self, obj: Download) -> str:
        return self._status_text(obj, Language.PL)

    @admin.display(description="angielski")
    def status_en(self, obj: Download) -> str:
        return self._status_text(obj, Language.EN)

    def _status_text(self, obj: Download, language_code: str) -> str:
        translation = obj.translations_by_language().get(language_code)
        if translation is None:
            return "brak wersji"
        return translation.get_status_display()
