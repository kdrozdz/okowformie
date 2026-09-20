"""Routing publicznego API brandingu strony.

Dołączany z `backend.urls` pod `/api/v1/`, tak jak `blog.urls`/`about.urls`.
Bez `{lang}` w ścieżce — logo i linki social media nie są tłumaczone, w
przeciwieństwie do treści bloga/strony „O mnie".
"""

from django.urls import path

from . import views

app_name = "branding"

urlpatterns = [
    path("branding/", views.SiteBrandingView.as_view(), name="branding-detail"),
]
