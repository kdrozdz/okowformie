"""Branding i nawigacja panelu redakcyjnego (Django Admin) jako całości.

Jedno miejsce importowane z `backend/urls.py` (tam, gdzie `admin.site.urls`
jest już zarejestrowany), zamiast rozrzucania konfiguracji per apka:
`site_header`/`site_title`/`index_title` i grupowanie strony głównej nie
należą do żadnej konkretnej domeny (`blog`/`about`/...), tylko do panelu
jako powierzchni — `.claude/rules/content-admin.md`, `docs/tasks/
15-motyw-panelu-admina.md`.
"""

from typing import Any

from django.contrib import admin
from django.http import HttpRequest

admin.site.site_header = "okowFormie — Panel redakcyjny"
admin.site.site_title = "okowFormie"
admin.site.index_title = "Panel redakcyjny"

#: Kolejność i skład kategorii na stronie głównej — spec w
#: `docs/tasks/15-motyw-panelu-admina.md` („Decyzje po drodze” → „Spec
#: kolorów/layoutu”). Klucz to `(app_label, model_name)` dokładnie tak, jak
#: budowane w `AdminSite._build_app_dict` (`model._meta.model_name`, zawsze
#: małymi literami) — dopisanie nowego modelu do panelu bez dopisania go
#: tutaj po prostu nie pojawi się w żadnej kategorii (fail-safe w stronę
#: "brak", nie w stronę "wyciek do złej kategorii").
_APP_LIST_CATEGORIES: tuple[tuple[str, str, tuple[tuple[str, str], ...]], ...] = (
    # (slug ASCII dla app_label/id w HTML, nazwa wyświetlana, modele)
    ("content", "Treść", (("blog", "post"), ("about", "aboutme"))),
    ("branding", "Branding", (("branding", "sitebranding"),)),
    (
        "ai-config",
        "Konfiguracja AI",
        (("ai_content", "aiprovidersettings"), ("ai_content", "postgenerator")),
    ),
    ("accounts", "Konta", (("accounts", "user"),)),
)


class OkowformieAdminSite(admin.AdminSite):
    """`AdminSite` z własnym grupowaniem strony głównej.

    Przypisana na już istniejącą instancję singletona `admin.site` niżej
    (`admin.site.__class__ = ...`), nie tworzona jako nowa instancja: każda
    domenowa apka rejestruje swoje modele przez `@admin.register`, co zawsze
    trafia do tego jednego, globalnego singletona
    (`django.contrib.admin.site`) — nowa instancja zerowałaby cały już
    zbudowany rejestr, gdyby ta klasa ładowała się po tamtych rejestracjach
    (a w Django kolejność importu apek nie jest gwarantowana w drugą stronę).
    """

    def get_app_list(
        self, request: HttpRequest, app_label: str | None = None
    ) -> list[dict[str, Any]]:
        """Zgrupuj już-przefiltrowane modele wg kategorii domenowych.

        `_build_app_dict` (Django) odfiltrowuje moduły/modele bez uprawnień
        (`has_module_permission`, `get_model_perms`) **przed** zwrotem —
        funkcja niżej tylko przekłada już przefiltrowany wynik na inny
        układ. Model, do którego użytkownik nie ma uprawnień, nie trafia do
        `app_dict` w ogóle, więc nie może trafić też do żadnej kategorii —
        grupowanie nie ujawnia niczego, co domyślny widok by ukrył.
        """
        app_dict = self._build_app_dict(request, app_label)
        models_by_key = {
            (model["model"]._meta.app_label, model["model"]._meta.model_name): model
            for app in app_dict.values()
            for model in app["models"]
        }

        grouped: list[dict[str, Any]] = []
        for slug, name, keys in _APP_LIST_CATEGORIES:
            models = [models_by_key[key] for key in keys if key in models_by_key]
            if not models:
                continue
            models.sort(key=lambda m: m["name"])
            # Link na nazwie kategorii prowadzi do pierwszego modelu — nie ma
            # odpowiednika `admin:app_list` dla kategorii, która nie jest
            # apką Django. "#" (nigdy podłańcuch `request.path`) zamiast "":
            # `app_list.html` sprawdza `app.app_url in request.path`, a
            # pusty string jest podłańcuchem każdego stringa — wszystkie
            # kategorie dostałyby fałszywie klasę `current-app`.
            first_url = next((m["admin_url"] for m in models if m.get("admin_url")), None)
            grouped.append(
                {
                    "name": name,
                    "app_label": slug,
                    "app_url": first_url or "#",
                    "has_module_perms": True,
                    "models": models,
                }
            )
        return grouped


admin.site.__class__ = OkowformieAdminSite
