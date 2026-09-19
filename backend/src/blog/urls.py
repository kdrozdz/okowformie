"""Routing publicznego API bloga.

Dołączany z `backend.urls` pod `/api/v1/` — ten moduł nie zna własnego
prefiksu wersji, żeby wersjonowanie zostało w jednym miejscu
(`.claude/rules/scope.md`: kontrakt wersjonowany `/api/v1/`).
"""

from django.urls import path

from . import views

app_name = "blog"

urlpatterns = [
    path("<str:lang>/posts/", views.PostListView.as_view(), name="post-list"),
    path("<str:lang>/posts/<slug:slug>/", views.PostDetailView.as_view(), name="post-detail"),
]
