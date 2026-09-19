"""Routing publicznego API strony „O mnie".

Dołączany z `backend.urls` pod `/api/v1/`, tak jak `blog.urls` — ten moduł
nie zna własnego prefiksu wersji (`.claude/rules/scope.md`: kontrakt
wersjonowany `/api/v1/`).
"""

from django.urls import path

from . import views

app_name = "about"

urlpatterns = [
    path("<str:lang>/about/", views.AboutDetailView.as_view(), name="about-detail"),
]
