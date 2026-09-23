"""Panel redakcyjny.

Kryterium akceptacji: post dodaje osoba nietechniczna, bez developera
(`.claude/rules/content-admin.md`). Stąd polskie etykiety, slug generowany
sam, SEO schowane w zwiniętej sekcji i kolumny, które od razu pokazują,
której wersji językowej brakuje.
"""

from typing import Any

from django.contrib import admin
from django.db.models import QuerySet
from django.http import HttpRequest
from django.utils.html import format_html
from django.utils.safestring import SafeString
from parler.admin import TranslatableAdmin

from .constants import Language, PostStatus
from .forms import PostAdminForm
from .models import Post, PostTranslation

#: Kolory kropek statusu na liście. Kolor jest dodatkiem do tekstu, nigdy
#: jedynym nośnikiem informacji — obok zawsze stoi nazwa statusu.
_STATUS_COLORS: dict[str, str] = {
    PostStatus.DRAFT: "#946200",
    PostStatus.PUBLISHED: "#1a7f37",
    PostStatus.ARCHIVED: "#6e7781",
}


def _translated_post_ids(
    language_code: str, **conditions: Any
) -> QuerySet[PostTranslation, dict[str, Any]]:
    """Id postów, których tłumaczenie w danym języku spełnia warunki."""
    return PostTranslation.objects.filter(language_code=language_code, **conditions).values(
        "master_id"
    )


class TranslationCompletenessFilter(admin.SimpleListFilter):
    """Filtr „czego brakuje".

    Przy kilkuset postach oko nie wyłapie z listy, że EN nie został
    dorobiony. Ten filtr odpowiada wprost na pytanie „co mam jeszcze do
    zrobienia" — osobno dla braku wersji i dla wersji nieopublikowanej,
    bo to dwa różne zadania.
    """

    title = "Kompletność tłumaczeń"
    parameter_name = "translations"

    def lookups(self, request: HttpRequest, model_admin: admin.ModelAdmin) -> list[tuple[str, str]]:
        lookups: list[tuple[str, str]] = []
        for language in Language:
            lookups.append((f"missing_{language.value}", f"Brak wersji {language.label}"))
            lookups.append(
                (f"unpublished_{language.value}", f"Wersja {language.label} nieopublikowana")
            )
        return lookups

    def queryset(self, request: HttpRequest, queryset: QuerySet[Post]) -> QuerySet[Post] | None:
        value = self.value()
        if not value:
            return None

        kind, _, language_code = value.partition("_")
        if language_code not in Language.values:
            return None

        if kind == "missing":
            return queryset.exclude(pk__in=_translated_post_ids(language_code))
        if kind == "unpublished":
            # Wersja istnieje, ale nie jest opublikowana — inny problem niż
            # brak wersji, więc inny wynik filtra.
            return queryset.filter(pk__in=_translated_post_ids(language_code)).exclude(
                pk__in=_translated_post_ids(language_code, status=PostStatus.PUBLISHED)
            )
        return None


@admin.register(Post)
class PostAdmin(TranslatableAdmin):
    form = PostAdminForm

    list_display = (
        "admin_title",
        "status_pl",
        "status_en",
        "author",
        "published_at_pl",
        "created_at",
    )
    list_filter = (
        TranslationCompletenessFilter,
        "translations__status",
        "author",
        "created_at",
    )
    search_fields = (
        "translations__title",
        "translations__slug",
        "translations__excerpt",
        "author__username",
    )
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
    list_per_page = 50

    fieldsets = (
        (
            None,
            {
                "fields": ("title", "slug", "author"),
                "description": (
                    "Zakładki u góry przełączają wersję językową tego samego posta. "
                    "Każdą wersję publikujesz osobno."
                ),
            },
        ),
        ("Treść", {"fields": ("excerpt", "content")}),
        (
            "Obraz okładki",
            {
                "fields": ("cover_image", "cover_image_alt"),
                "description": "Obraz jest wspólny dla obu języków, opis (alt) osobny.",
            },
        ),
        ("Publikacja", {"fields": ("status", "published_at")}),
        (
            "SEO",
            {
                "classes": ("collapse",),
                "fields": ("meta_title", "meta_description"),
                "description": (
                    "Możesz zostawić puste — wtedy użyjemy tytułu i zajawki. "
                    "Tytuł SEO do 60 znaków, opis SEO najlepiej 150–160 znaków."
                ),
            },
        ),
    )

    def get_fieldsets(
        self, request: HttpRequest, obj: Post | None = None
    ) -> tuple[tuple[str | None, dict[str, Any]], ...]:
        """Przy dodawaniu autorem jest zawsze zalogowany redaktor — pole zbędne.

        Widoczne dopiero przy edycji, żeby superuser mógł w razie potrzeby
        przepiąć istniejący post na innego autora (np. porządki po odejściu
        redaktora). `save_model` i tak podstawia `request.user`, gdy pole
        jest nieobecne na formularzu dodawania — patrz komentarz tam.
        """
        fieldsets = super().get_fieldsets(request, obj)
        if obj is not None:
            return tuple(fieldsets)

        without_author: list[tuple[str | None, dict[str, Any]]] = []
        for name, options in fieldsets:
            if name is not None or "author" not in options["fields"]:
                without_author.append((name, options))
                continue
            without_author.append(
                (name, {**options, "fields": tuple(f for f in options["fields"] if f != "author")})
            )
        return tuple(without_author)

    def formfield_for_foreignkey(self, db_field: Any, request: HttpRequest, **kwargs: Any) -> Any:
        """Dropdown autora pokazuje tylko konta staff.

        `Post.author` celowo nie ma `limit_choices_to` na poziomie modelu
        (`blog/models.py`) — ograniczenie tam objęłoby też przyszłe
        programowe tworzenie postów (import, API zapisu w fazie 2), które
        nie powinno zakładać, że autor musi mieć dostęp do panelu. To
        ograniczenie jest tylko UX-em admina: w fazie 2 ten sam model
        `User` zacznie obsługiwać też konta klientów, których nie ma co
        pokazywać na liście autorów.
        """
        if db_field.name == "author":
            kwargs["queryset"] = db_field.remote_field.model._default_manager.filter(is_staff=True)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_prepopulated_fields(
        self, request: HttpRequest, obj: Post | None = None
    ) -> dict[str, tuple[str, ...]]:
        """Slug podpowiada się w przeglądarce w trakcie pisania tytułu.

        To tylko wygoda. Gwarancją jest `PostTranslation.save()`, które i tak
        dogeneruje slug — redaktor nigdy nie musi go wpisać ręcznie.
        (`prepopulated_fields` nie da się użyć wprost: pola tłumaczone nie
        przechodzą walidacji admina, stąd `get_prepopulated_fields`.)
        """
        return {"slug": ("title",)}

    def get_queryset(self, request: HttpRequest) -> QuerySet[Post]:
        """Jedno zapytanie na autorów i jedno na wszystkie tłumaczenia.

        Bez tego każda kolumna statusu odpytywałaby bazę per wiersz — przy
        50 postach na stronie to 100 zapytań (`.claude/rules/performance.md`).

        `.distinct()` jest tu konieczne, nie kosmetyczne: `list_filter`
        (`translations__status`) robi JOIN na `translations` — bez
        `.distinct()` post z dwoma tłumaczeniami (PL+EN) pasującymi do
        filtra pojawia się na liście dwa razy. Ten sam wzorzec naprawy co
        `downloads.admin.DownloadAdmin.get_queryset` — patrz tam po pełne
        wyjaśnienie (empirycznie zweryfikowane przy `docs/tasks/16-pliki-do-pobrania.md`,
        znalezisko przeniesione do `blog` w `docs/todo/TODO.md`).
        """
        return (
            super()
            .get_queryset(request)
            .select_related("author")
            .prefetch_related("translations")
            .distinct()
        )

    def save_model(self, request: HttpRequest, obj: Post, form: Any, change: bool) -> None:
        """Domyślnym autorem jest osoba zakładająca post.

        Pole `author` jest ukryte na formularzu dodawania (`get_fieldsets`),
        więc formularz nigdy go tam nie ustawia na `obj` — `obj.author_id`
        zostaje puste i bezwarunkowy fallback go uzupełnia. Przy edycji pole
        jest widoczne i wymagane, więc `form.save(commit=False)` już ustawiło
        `obj.author` zanim `save_model` się wykonało — warunek nic wtedy nie
        nadpisuje.
        """
        if not obj.author_id:
            obj.author = request.user
        super().save_model(request, obj, form, change)

    # --- Kolumny listy --------------------------------------------------

    @admin.display(description="Tytuł")
    def admin_title(self, obj: Post) -> str:
        """Bez `ordering="translations__title"` — celowo, tak jak
        `downloads.admin.DownloadAdmin.admin_title`. `.distinct()` w
        `get_queryset()` naprawia duplikaty z JOIN-a przy filtrowaniu, ale
        nie przy sortowaniu po kolumnie z JOIN-a: Postgres wymaga, żeby
        `SELECT DISTINCT` zawierał w SELECT każdą kolumnę z `ORDER BY`, więc
        `title` z dwóch różnych tłumaczeń tego samego posta robi z
        (`id`, `title`) dwie różne „distinct" krotki — post z dwoma
        tłumaczeniami nadal pojawiałby się na liście dwa razy po kliknięciu
        nagłówka kolumny. Lista ma kanoniczne sortowanie po `-created_at`
        (`Meta.ordering`/`ordering` w tej klasie) — klikalne sortowanie
        alfabetyczne po tytule nie było wymaganiem.
        """
        return obj.safe_translation_getter("title", any_language=True) or "(bez tytułu)"

    @admin.display(description="Data publikacji (PL)")
    def published_at_pl(self, obj: Post) -> Any:
        translation = obj.translations_by_language().get(Language.PL)
        return translation.published_at if translation else None

    @admin.display(description="polski")
    def status_pl(self, obj: Post) -> SafeString:
        return self._status_badge(obj, Language.PL)

    @admin.display(description="angielski")
    def status_en(self, obj: Post) -> SafeString:
        return self._status_badge(obj, Language.EN)

    def _status_badge(self, obj: Post, language_code: str) -> SafeString:
        translation = obj.translations_by_language().get(language_code)
        if translation is None:
            return format_html('<span style="color:{}">&#9679; {}</span>', "#b42318", "brak wersji")
        return format_html(
            '<span style="color:{}">&#9679; {}</span>',
            _STATUS_COLORS.get(translation.status, "#6e7781"),
            translation.get_status_display(),
        )
