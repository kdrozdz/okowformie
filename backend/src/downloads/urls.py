"""Routing publicznego API plików do pobrania.

Dołączany z `backend.urls` pod `/api/v1/` — ten moduł nie zna własnego
prefiksu wersji, żeby wersjonowanie zostało w jednym miejscu
(`.claude/rules/scope.md`: kontrakt wersjonowany `/api/v1/`), tak jak
`blog.urls`/`about.urls`.
"""

from django.urls import path

from . import views

app_name = "downloads"

urlpatterns = [
    path("<str:lang>/downloads/", views.DownloadListView.as_view(), name="download-list"),
]
