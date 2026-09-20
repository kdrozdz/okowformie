"""Panel redakcyjny brandingu strony (logo + linki social media).

Kryterium akceptacji jak przy `about`: dodawane i edytowane przez osobę
nietechniczną (`.claude/rules/content-admin.md`). To singleton, więc panel
ma uniemożliwiać dodanie drugiego rekordu i prowadzić od razu do edycji, z
pominięciem listy jednoelementowej — wzorzec 1:1 z `about.admin.AboutMeAdmin`.
"""

from typing import Any

from django.contrib import admin
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.utils.safestring import SafeString

from .icons import social_platform_icon_html
from .models import SiteBranding, SocialLink

#: Linki social media edytuje się wyłącznie przez `SocialLinkInline` w
#: `SiteBranding` — brak osobnej rejestracji `SocialLink` w adminie jest
#: celowy, tak samo jak `about.models.Certificate` nie ma własnego wpisu
#: obok `AboutMe` (`.claude/rules/content-admin.md`: jedno miejsce edycji).


class SocialLinkInline(admin.TabularInline):
    """Lista linków social media wewnątrz formularza `SiteBranding`, sortowana ręcznie.

    Standardowy `TabularInline` (`can_delete` domyślnie włączone) — redaktor
    dodaje nowe wiersze przez `extra=1` i usuwa istniejące checkboxem, bez
    dodatkowej konfiguracji.
    """

    model = SocialLink
    fk_name = "branding"
    extra = 1
    fields = ("platform_icon", "platform", "url", "order")
    readonly_fields = ("platform_icon",)
    ordering = ("order", "id")

    @admin.display(description="")
    def platform_icon(self, obj: SocialLink) -> SafeString:
        """Podgląd ikonki platformy obok dropdowna — redaktor rozpoznaje
        wiersz bez czytania tekstu `get_platform_display()`
        (`.claude/rules/content-admin.md`: panel dla osoby nietechnicznej).

        Pusty label (`description=""`) — kolumna z samą ikonką nie potrzebuje
        nagłówka, `platform` obok niej już opisuje treść wiersza. Puste
        `obj.platform` (nowy, jeszcze niewypełniony wiersz `extra`) trafia do
        tej samej gałęzi placeholdera co nieznana platforma w
        `social_platform_icon_html`.
        """
        return social_platform_icon_html(obj.platform)


@admin.register(SiteBranding)
class SiteBrandingAdmin(admin.ModelAdmin):
    inlines = (SocialLinkInline,)
    fields = ("logo",)

    def has_add_permission(self, request: HttpRequest) -> bool:
        """Singleton: drugi rekord nigdy nie może powstać z panelu.

        Blokuje też bezpośrednie wejście na `.../sitebranding/add/` — Django
        sprawdza to samo uprawnienie w `add_view`, niezależnie od tego, czy
        redaktor trafił tam linkiem, czy wpisał adres ręcznie.
        """
        if SiteBranding.objects.exists():
            return False
        return super().has_add_permission(request)

    def changelist_view(
        self, request: HttpRequest, extra_context: Any = None
    ) -> HttpResponse:
        """Pomiń listę jednoelementową — od razu edycja albo dodanie singletona.

        Uprawnienia trzeba sprawdzić **tutaj**, przed policzeniem adresu do
        przekierowania — patrz uzasadnienie w `about.admin.AboutMeAdmin.changelist_view`:
        bez tej kontroli dowolne konto `is_staff=True` bez uprawnień do
        `SiteBranding` dostawało `302` z adresem zawierającym PK rekordu,
        czyli wyciek metadanych, jakiego standardowy `changelist_view` w
        ogóle by nie dał (zwróciłby `403`).
        """
        if not self.has_view_or_change_permission(request):
            return super().changelist_view(request, extra_context)
        if (branding := SiteBranding.objects.first()) is not None:
            return HttpResponseRedirect(
                reverse("admin:branding_sitebranding_change", args=[branding.pk])
            )
        return HttpResponseRedirect(reverse("admin:branding_sitebranding_add"))

    def get_queryset(self, request: HttpRequest) -> Any:
        """Jedno zapytanie na linki social media — wzorzec `AboutMeAdmin.get_queryset`
        (`.claude/rules/performance.md`)."""
        return super().get_queryset(request).prefetch_related("social_links")
