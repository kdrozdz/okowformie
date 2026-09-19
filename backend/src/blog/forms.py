"""Formularz panelu redakcyjnego.

Cała walidacja mówi po polsku i mówi **co zrobić**, nie co się zepsuło
(`.claude/rules/content-admin.md`). Komunikaty są tutaj, a nie w modelu,
bo to warstwa rozmowy z redaktorem; model pilnuje niezmienników twardo
(ograniczenia bazy, sanityzacja w `save()`).
"""

from typing import Any

from django import forms
from django.conf import settings
from django.utils.html import strip_tags
from django_prose_editor.widgets import AdminProseEditorWidget
from parler.forms import TranslatableModelForm

from .constants import (
    META_DESCRIPTION_MAX_LENGTH,
    META_DESCRIPTION_MIN_LENGTH,
    META_TITLE_MAX_LENGTH,
    PostStatus,
)
from .models import Post, PostTranslation
from .slugs import build_unique_slug


def language_label(language_code: str) -> str:
    """Nazwa języka po polsku, do wstawienia w komunikat błędu."""
    return dict(settings.LANGUAGES).get(language_code, language_code)


class PostAdminForm(TranslatableModelForm):
    """Jeden formularz na post: pola wspólne + pola bieżącej wersji językowej.

    `django-parler` podstawia `language_code` klasie formularza przy każdej
    zakładce językowej, więc walidacja poniżej zawsze wie, którą wersję
    właśnie sprawdza.
    """

    class Meta:
        model = Post
        fields = "__all__"
        widgets = {
            # Zajawka to kilka zdań — jednolinijkowy `input` zachęcałby do
            # pisania jednego zdania bez oddechu.
            "excerpt": forms.Textarea(attrs={"rows": 3}),
            "cover_image_alt": forms.TextInput(attrs={"size": 80}),
            # Wariant widgetu dopasowany stylami do panelu. Parler buduje
            # pola tłumaczone poza `formfield_overrides` admina, więc admin
            # sam by go nie podmienił.
            "content": AdminProseEditorWidget,
        }

    def clean(self) -> dict[str, Any]:
        cleaned: dict[str, Any] = super().clean()
        self._validate_slug_free(cleaned)
        self._validate_seo(cleaned)
        self._validate_ready_to_publish(cleaned)
        return cleaned

    # --- Slug ----------------------------------------------------------

    def _validate_slug_free(self, cleaned: dict[str, Any]) -> None:
        """Slug musi być wolny **w tym języku**.

        Parler woła `validate_constraints()` z `language_code` na liście
        wykluczeń, więc ograniczenie z bazy nie odpali się na formularzu —
        bez tej walidacji redaktor dostałby `IntegrityError` zamiast
        komunikatu. Pusty slug pomijamy: dogeneruje go `save()` modelu.
        """
        slug = cleaned.get("slug")
        if not slug:
            return

        taken = PostTranslation.objects.filter(language_code=self.language_code, slug=slug)
        if self.instance.pk:
            taken = taken.exclude(master_id=self.instance.pk)
        if not taken.exists():
            return

        suggestion = build_unique_slug(
            slug,
            is_taken=lambda candidate: (
                PostTranslation.objects.filter(language_code=self.language_code, slug=candidate)
                .exclude(master_id=self.instance.pk or 0)
                .exists()
            ),
            max_length=PostTranslation._meta.get_field("slug").max_length or 220,
        )
        self.add_error(
            "slug",
            forms.ValidationError(
                "Ten adres jest już zajęty przez inny post w wersji %(language)s. "
                'Wpisz inny — na przykład „%(suggestion)s".',
                code="slug_taken",
                params={"language": language_label(self.language_code), "suggestion": suggestion},
            ),
        )

    # --- SEO -----------------------------------------------------------

    def _validate_seo(self, cleaned: dict[str, Any]) -> None:
        meta_title = cleaned.get("meta_title") or ""
        if len(meta_title) > META_TITLE_MAX_LENGTH:
            self.add_error(
                "meta_title",
                forms.ValidationError(
                    "Tytuł SEO ma %(length)d znaków. Skróć go o %(excess)d, "
                    "bo wyszukiwarka i tak pokaże tylko %(limit)d pierwszych.",
                    code="meta_title_too_long",
                    params={
                        "length": len(meta_title),
                        "excess": len(meta_title) - META_TITLE_MAX_LENGTH,
                        "limit": META_TITLE_MAX_LENGTH,
                    },
                ),
            )

        meta_description = cleaned.get("meta_description") or ""
        if not meta_description:
            # Puste jest w porządku — zadziała fallback na zajawkę.
            return

        length = len(meta_description)
        if length < META_DESCRIPTION_MIN_LENGTH:
            self.add_error(
                "meta_description",
                forms.ValidationError(
                    "Opis SEO ma %(length)d znaków. Dopisz jeszcze co najmniej "
                    "%(missing)d — krótszy opis marnuje miejsce w wynikach wyszukiwania. "
                    "Możesz też zostawić pole puste, wtedy użyjemy zajawki.",
                    code="meta_description_too_short",
                    params={"length": length, "missing": META_DESCRIPTION_MIN_LENGTH - length},
                ),
            )
        elif length > META_DESCRIPTION_MAX_LENGTH:
            self.add_error(
                "meta_description",
                forms.ValidationError(
                    "Opis SEO ma %(length)d znaków. Skróć go o %(excess)d, "
                    "bo dłuższy zostanie ucięty w połowie zdania.",
                    code="meta_description_too_long",
                    params={
                        "length": length,
                        "excess": length - META_DESCRIPTION_MAX_LENGTH,
                    },
                ),
            )

    # --- Gotowość do publikacji -------------------------------------------

    def _validate_ready_to_publish(self, cleaned: dict[str, Any]) -> None:
        """Nie wypuszczaj pustej strony pod publiczny adres."""
        if cleaned.get("status") != PostStatus.PUBLISHED:
            return

        missing: list[str] = []
        if not (cleaned.get("title") or "").strip():
            missing.append("tytuł")
        if not (cleaned.get("excerpt") or "").strip():
            missing.append("zajawkę")
        if not strip_tags(cleaned.get("content") or "").strip():
            missing.append("treść")

        if missing:
            self.add_error(
                "status",
                forms.ValidationError(
                    "Aby opublikować wersję %(language)s, uzupełnij: %(missing)s. "
                    'Do tego czasu zostaw status „Szkic".',
                    code="not_ready_to_publish",
                    params={
                        "language": language_label(self.language_code),
                        "missing": ", ".join(missing),
                    },
                ),
            )

        if cleaned.get("cover_image") and not (cleaned.get("cover_image_alt") or "").strip():
            self.add_error(
                "cover_image_alt",
                forms.ValidationError(
                    "Opisz jednym zdaniem, co widać na okładce. Bez tego osoby "
                    "niewidome nie dowiedzą się, co jest na obrazku.",
                    code="missing_cover_image_alt",
                ),
            )
