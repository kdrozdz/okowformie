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

        `.distinct()` jest tu konieczne, nie kosmetyczne: `list_filter`
        (`translations__status`) i sortowanie po kolumnie „Nazwa”
        (`ordering="translations__title"` w `admin_title`) robią JOIN na
        `translations` — bez `.distinct()` plik z dwoma tłumaczeniami (PL+EN)
        pasującymi do filtra/sortowania pojawia się na liście dwa razy
        (zweryfikowane empirycznie: `qs.filter(translations__status=...)`
        zwraca ten sam `pk` dwa razy). Django admin dodaje `.distinct()`
        automatycznie tylko dla JOIN-ów z `search_fields`, nie z
        `list_filter`/`ordering`.
        """
        return super().get_queryset(request).prefetch_related("translations").distinct()

    # --- Kolumny listy --------------------------------------------------

    @admin.display(description="Nazwa")
    def admin_title(self, obj: Download) -> str:
        """Bez `ordering="translations__title"` (w przeciwieństwie do
        `blog.admin.PostAdmin.admin_title`) — celowo. `.distinct()` w
        `get_queryset()` wyżej naprawia duplikaty wynikające z JOIN-a przy
        filtrowaniu (`list_filter`), ale **nie** przy sortowaniu po kolumnie z
        JOIN-a: Postgres wymaga, żeby `SELECT DISTINCT` zawierał w SELECT
        każdą kolumnę użytą w `ORDER BY`, więc `title` z dwóch różnych
        tłumaczeń tego samego pliku robi z (`id`, `title`) dwie różne,
        „distinct” krotki — plik z dwoma tłumaczeniami nadal pojawiłby się na
        liście dwa razy po kliknięciu nagłówka kolumny (zweryfikowane
        empirycznie: `?o=1` dawał dwa wiersze dla tego samego `pk`, mimo
        `.distinct()`). Lista i tak ma kanoniczne, kuratorowane sortowanie po
        polu `order` (`Meta.ordering`) — klikalne sortowanie alfabetyczne po
        nazwie nie było wymaganiem, więc usunięcie go jest prostszą naprawą
        niż subquery/annotate zamiast surowego JOIN-a.
        """
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
