"""URL configuration dla projektu `backend`."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import HttpRequest, JsonResponse
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from . import admin as _admin_theme  # noqa: F401 — patrz komentarz niżej
from .settings import ADMIN_URL

# `django.contrib.admin` odkryłby `backend.admin` sam przez autodiscover na
# starcie Django, nawet bez importu wyżej — import jest tutaj jawnie, obok
# rejestracji `admin.site.urls` niżej, żeby zależność (branding + grupowanie
# strony głównej panelu, `backend/admin.py`) było widać bez znajomości tego
# mechanizmu Django.


def healthz(request: HttpRequest) -> JsonResponse:
    """Health-check dla Docker/orkiestracji — zawsze 200, bez zależności od bazy."""
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path(ADMIN_URL, admin.site.urls),
    path("healthz/", healthz, name="healthz"),
    # Kontrakt wersjonowany (`.claude/rules/scope.md`) — schema/docs tutaj,
    # bo obejmują wszystkie domeny API, nie tylko `blog`.
    path("api/v1/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/v1/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="api-docs",
    ),
    path("api/v1/", include("blog.urls")),
    path("api/v1/", include("about.urls")),
    path("api/v1/", include("branding.urls")),
    path("api/v1/", include("downloads.urls")),
]

if settings.DEBUG:
    # Serwowanie mediów przez Django samo tylko w dev — na produkcji obrazy
    # idą przez reverse proxy/CDN, nigdy przez proces aplikacji
    # (`.claude/rules/security.md`). Bez tego `MEDIA_URL` zwrócony przez
    # publiczne API (okładki postów, zdjęcie i certyfikaty „O mnie") jest
    # martwym linkiem w lokalnym środowisku.
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
