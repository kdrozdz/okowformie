"""URL configuration dla projektu `backend`."""

from django.contrib import admin
from django.http import HttpRequest, JsonResponse
from django.urls import path

from .settings import ADMIN_URL


def healthz(request: HttpRequest) -> JsonResponse:
    """Health-check dla Docker/orkiestracji — zawsze 200, bez zależności od bazy."""
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path(ADMIN_URL, admin.site.urls),
    path("healthz/", healthz, name="healthz"),
    # /api/v1/ dołoży się wraz z pierwszym endpointem domenowym.
]
