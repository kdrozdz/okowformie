"""Panel redakcyjny strony „O mnie".

Kryterium akceptacji jak przy blogu: strona jest dodawana i edytowana przez
osobę nietechniczną (`.claude/rules/content-admin.md`). Dodatkowo: to
singleton, więc panel ma uniemożliwiać dodanie drugiego rekordu i (o ile to
prosty dodatek — patrz niżej) prowadzić od razu do edycji, z pominięciem
listy jednoelementowej.
"""

from typing import Any

from django.contrib import admin
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.urls import reverse
from parler.admin import TranslatableAdmin

from .forms import AboutMeAdminForm
from .models import AboutMe, Certificate

#: Certyfikaty edytuje się wyłącznie przez `CertificateInline` w `AboutMe` —
#: brak osobnej rejestracji `Certificate` w adminie jest celowe. Drugie
#: miejsce edycji tego samego rekordu myliłoby jedyną, nietechniczną osobę
#: redagującą tę stronę (`.claude/rules/content-admin.md`), tak samo jak
#: `blog.models.PostTranslation` nie ma własnego wpisu w adminie obok `Post`.


class CertificateInline(admin.TabularInline):
    """Lista certyfikatów wewnątrz formularza `AboutMe`, sortowana ręcznie."""

    model = Certificate
    fk_name = "about"
    extra = 1
    fields = ("name", "issuer", "issued_year", "image", "order")
    ordering = ("order", "id")


@admin.register(AboutMe)
class AboutMeAdmin(TranslatableAdmin):
    form = AboutMeAdminForm
    inlines = (CertificateInline,)

    fieldsets = (
        (
            None,
            {
                "fields": ("full_name", "headline"),
                "description": (
                    "Zakładki u góry przełączają wersję językową tej samej strony. "
                    "Każdą wersję publikujesz osobno."
                ),
            },
        ),
        ("Biografia", {"fields": ("bio",)}),
        (
            "Zdjęcie",
            {
                "fields": ("photo", "photo_alt"),
                "description": "Zdjęcie jest wspólne dla obu języków, opis (alt) osobny.",
            },
        ),
        ("Publikacja", {"fields": ("status", "published_at")}),
        (
            "SEO",
            {
                "classes": ("collapse",),
                "fields": ("meta_title", "meta_description"),
                "description": (
                    "Możesz zostawić puste — wtedy użyjemy nagłówka. "
                    "Tytuł SEO do 60 znaków, opis SEO najlepiej 150–160 znaków."
                ),
            },
        ),
    )

    def has_add_permission(self, request: HttpRequest) -> bool:
        """Singleton: drugi rekord nigdy nie może powstać z panelu.

        Blokuje też bezpośrednie wejście na `.../aboutme/add/` — Django
        sprawdza to samo uprawnienie w `add_view`, niezależnie od tego, czy
        redaktor trafił tam linkiem, czy wpisał adres ręcznie.
        """
        if AboutMe.objects.exists():
            return False
        return super().has_add_permission(request)

    def changelist_view(
        self, request: HttpRequest, extra_context: Any = None
    ) -> HttpResponse:
        """Pomiń listę jednoelementową — od razu edycja albo dodanie singletona.

        Prosty redirect, nie hack na formularzu ani na routingu: lista i tak
        zawsze ma 0 albo 1 wiersz, więc pokazywanie jej nie daje redaktorowi
        żadnej informacji, którą i tak nie dostałby szybciej wprost z edycji.

        Uprawnienia trzeba sprawdzić **tutaj**, przed policzeniem adresu do
        przekierowania: samo `.../change/`, na które prowadzi redirect, i tak
        zablokuje dostęp osobnym sprawdzeniem w `change_view`, ale bez tej
        kontroli dowolne konto `is_staff=True` bez żadnych uprawnień do
        `AboutMe` dostawało `302` z adresem zawierającym PK rekordu —
        potwierdzenie istnienia wpisu i jego identyfikator, czyli wyciek
        metadanych, jakiego standardowy `changelist_view` w ogóle by nie dał
        (zwróciłby `403`). Gdy uprawnień brakuje, oddajemy sterowanie
        standardowej implementacji Django, która sama zwraca `403`.
        """
        if not self.has_view_or_change_permission(request):
            return super().changelist_view(request, extra_context)
        if (about := AboutMe.objects.first()) is not None:
            return HttpResponseRedirect(reverse("admin:about_aboutme_change", args=[about.pk]))
        return HttpResponseRedirect(reverse("admin:about_aboutme_add"))

    def get_queryset(self, request: HttpRequest) -> Any:
        """Jedno zapytanie na certyfikaty i jedno na wszystkie tłumaczenia.

        Analogiczne do `blog.admin.PostAdmin.get_queryset`
        (`.claude/rules/performance.md`) — tu na jednym wierszu nie robi
        różnicy w praktyce, ale trzyma spójny wzorzec i nie regresuje, gdyby
        w przyszłości ktoś dodał więcej singletonów obok siebie na jednej liście.
        """
        return (
            super()
            .get_queryset(request)
            .prefetch_related("translations", "certificates")
        )
