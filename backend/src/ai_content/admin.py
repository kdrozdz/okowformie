"""Panel redakcyjny generatora postów AI.

Dwie rejestracje tego samego rekordu (`.claude/rules/content-admin.md` +
`ai_content/models.py`, docstring `PostGenerator`):

- `AIProviderSettingsAdmin` — zakładka „Ustawienia AI", zwykła edycja
  singletona, wzorowana 1:1 na `about.admin.AboutMeAdmin`.
- `PostGeneratorAdmin` — zakładka „Post z AI", renderuje formularz
  generowania zamiast standardowego CRUD-u admina; logika biznesowa (wywołanie
  LLM, zapis szkicu) żyje w `ai_content.services`, ten widok tylko woła te
  funkcje i tłumaczy wynik na `django.contrib.messages`
  (`.claude/rules/engineering-principles.md`).
"""

from typing import Any

from django.contrib import admin, messages
from django.contrib.auth.models import AbstractUser
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.html import format_html

from .forms import PostGenerationForm
from .models import AIProviderSettings, PostGenerator
from .services import (
    PostGenerationError,
    create_draft_post_from_generated_content,
    generate_post_content,
)


@admin.register(AIProviderSettings)
class AIProviderSettingsAdmin(admin.ModelAdmin):
    fields = ("provider", "model_name", "temperature", "max_output_tokens")

    def has_add_permission(self, request: HttpRequest) -> bool:
        """Singleton: drugi rekord nigdy nie może powstać z panelu.

        Blokuje też bezpośrednie wejście na `.../aiprovidersettings/add/` —
        Django sprawdza to samo uprawnienie w `add_view`, niezależnie od
        tego, czy redaktor trafił tam linkiem, czy wpisał adres ręcznie.
        """
        if AIProviderSettings.objects.exists():
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
        `AIProviderSettings` dostawało `302` z adresem zawierającym PK
        rekordu — potwierdzenie istnienia wpisu i jego identyfikator, czyli
        wyciek metadanych, jakiego standardowy `changelist_view` w ogóle by
        nie dał (zwróciłby `403`). Gdy uprawnień brakuje, oddajemy sterowanie
        standardowej implementacji Django, która sama zwraca `403`.
        """
        if not self.has_view_or_change_permission(request):
            return super().changelist_view(request, extra_context)
        if (settings_obj := AIProviderSettings.objects.first()) is not None:
            return HttpResponseRedirect(
                reverse("admin:ai_content_aiprovidersettings_change", args=[settings_obj.pk])
            )
        return HttpResponseRedirect(reverse("admin:ai_content_aiprovidersettings_add"))


@admin.register(PostGenerator)
class PostGeneratorAdmin(admin.ModelAdmin):
    """Formularz „Post z AI" zamiast generycznego CRUD-u admina.

    Jedyna droga zapisu jest przez `changelist_view` niżej (wywołanie
    `ai_content.services`, nigdy bezpośrednia edycja pól modelu z tego
    widoku) — stąd `has_add_permission`/`has_change_permission`/
    `has_delete_permission` zawsze `False`: nie ma tu nic do dodania,
    zmiany ani skasowania w sensie, jaki rozumie Django Admin.
    """

    def has_module_permission(self, request: HttpRequest) -> bool:
        return request.user.has_perm("blog.add_post")

    def has_view_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return request.user.has_perm("blog.add_post")

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False

    def changelist_view(
        self, request: HttpRequest, extra_context: Any = None
    ) -> HttpResponse:
        """Renderuj i obsłuż formularz generowania zamiast listy/CRUD-u.

        Sprawdzenie uprawnień **przed** jakąkolwiek dalszą logiką — ten sam
        wzorzec 403 co `AIProviderSettingsAdmin.changelist_view`: bez niego
        osoba bez `blog.add_post` mogłaby wywnioskować istnienie tej
        zakładki z zachowania widoku, zamiast dostać `403` wprost.
        """
        if not self.has_view_or_change_permission(request):
            return super().changelist_view(request, extra_context)

        if request.method == "POST":
            form = PostGenerationForm(request.POST)
        else:
            form = PostGenerationForm()

        if request.method == "POST" and form.is_valid():
            ai_settings = AIProviderSettings.objects.first()
            if ai_settings is None:
                messages.error(
                    request,
                    "Najpierw skonfiguruj dostawcę AI w zakładce „Ustawienia AI”.",
                )
            else:
                # `request.user` jest typowany jako `AbstractBaseUser | AnonymousUser`
                # (Django/django-stubs nie zawężają go automatycznie na
                # podstawie `login_required`). `has_view_or_change_permission`
                # wyżej już zagwarantował, że to zalogowany staff — ten
                # `assert` tylko potwierdza to mypy, bez zmiany zachowania.
                assert isinstance(request.user, AbstractUser)
                try:
                    generated = generate_post_content(
                        topic=form.cleaned_data["topic"],
                        local_focus=form.cleaned_data["local_focus"],
                        ai_settings=ai_settings,
                    )
                    post = create_draft_post_from_generated_content(
                        generated, author=request.user
                    )
                except PostGenerationError as exc:
                    messages.error(request, str(exc))
                else:
                    messages.success(
                        request,
                        format_html(
                            'Post „{}” utworzony jako szkic. <a href="{}">Edytuj</a>. '
                            "Uzasadnienie SEO: {}",
                            generated.title,
                            reverse("admin:blog_post_change", args=[post.pk]),
                            generated.seo_rationale,
                        ),
                    )
                    return HttpResponseRedirect(reverse("admin:blog_post_change", args=[post.pk]))

        context = {
            **self.admin_site.each_context(request),
            "form": form,
            "title": "Post z AI",
            "opts": self.model._meta,
        }
        return TemplateResponse(
            request, "admin/ai_content/postgenerator/changelist.html", context
        )
