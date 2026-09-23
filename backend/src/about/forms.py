"""Formularz panelu redakcyjnego strony „O mnie".

Ten sam wzorzec walidacji co `blog.forms.PostAdminForm` — komunikaty po
polsku, mówiące **co zrobić**, nie co się zepsuło (`.claude/rules/content-admin.md`).
Bez logiki slugu: strona „O mnie" nie ma własnego adresu URL, jest
singletonem pod stałą ścieżką na froncie.
"""

from typing import Any

from django import forms
from django.utils.html import strip_tags
from django_prose_editor.widgets import AdminProseEditorWidget
from parler.forms import TranslatableModelForm

from core.constants import META_DESCRIPTION_MIN_LENGTH
from core.constants import PublicationStatus as AboutStatus
from core.i18n import language_label

from .models import AboutMe


class AboutMeAdminForm(TranslatableModelForm):
    """Jeden formularz na stronę: pola wspólne + pola bieżącej wersji językowej."""

    class Meta:
        model = AboutMe
        fields = "__all__"
        widgets = {
            "photo_alt": forms.TextInput(attrs={"size": 80}),
            # Ten sam wzorzec co `blog.forms.PostAdminForm.Meta.widgets` —
            # domyślny `TextInput` był węższy niż `photo_alt` mimo podobnej
            # długości treści (`docs/tasks/15-motyw-panelu-admina.md`).
            "meta_title": forms.TextInput(attrs={"size": 80}),
            "meta_description": forms.Textarea(attrs={"rows": 3}),
            # Parler buduje pola tłumaczone poza `formfield_overrides` admina,
            # więc admin sam by go nie podmienił (jak w `blog.forms.PostAdminForm`).
            "bio": AdminProseEditorWidget,
        }
        # Django odrzuca `headline` puste i `meta_title`/`meta_description`
        # za długie na poziomie pola formularza — **przed** `clean()` niżej —
        # więc przyjazny komunikat musi siedzieć tutaj, nie w
        # `_validate_seo`/`_validate_ready_to_publish` (te gałęzie były martwe:
        # `cleaned_data` nie zawiera już odrzuconej wartości, kiedy tamten kod
        # by się wykonał). `django-parler` czyta `Meta.error_messages` dla pól
        # tłumaczonych dokładnie tak samo jak Django dla zwykłych
        # (`TranslatableModelFormMetaclass._get_model_form_field`).
        #
        # Uwaga: `error_messages` ustawiony **na polu modelu**
        # (`models.CharField(error_messages=...)`) tu by nie zadziałał —
        # `Field.formfield()` w Django nie przenosi `error_messages` modelu do
        # formularza automatycznie (zweryfikowane w trakcie naprawy tego
        # defektu), więc jedynym miejscem, gdzie te komunikaty faktycznie
        # trafiają do `forms.CharField`, jest `Meta.error_messages` formularza.
        error_messages = {
            "headline": {
                "required": (
                    "Nagłówek jest wymagany — bez niego strona nie ma tytułu. "
                    'Np. „Optometrysta, właściciel gabinetu".'
                ),
            },
            "meta_title": {
                "max_length": (
                    "Tytuł SEO ma %(show_value)d znaków, maksimum to %(limit_value)d. "
                    "Skróć go — wyszukiwarka i tak pokaże tylko pierwsze %(limit_value)d."
                ),
            },
            "meta_description": {
                "max_length": (
                    "Opis SEO ma %(show_value)d znaków, maksimum to %(limit_value)d. "
                    "Skróć go, bo dłuższy zostanie ucięty w połowie zdania."
                ),
            },
        }

    def clean(self) -> dict[str, Any]:
        cleaned: dict[str, Any] = super().clean()
        self._validate_seo(cleaned)
        self._validate_ready_to_publish(cleaned)
        return cleaned

    # --- SEO -----------------------------------------------------------

    def _validate_seo(self, cleaned: dict[str, Any]) -> None:
        """Za długie `meta_title`/`meta_description` są już odrzucane na
        poziomie pola formularza (`Meta.error_messages`, klucz `max_length`)
        — Django woła `run_validators()` zanim ten `clean()` w ogóle się
        wykona. Jedyna gałąź, która faktycznie dociera tutaj, to „za krótki
        opis SEO": to reguła biznesowa bez odpowiednika w polu modelu
        (`min_length` nie jest tam ustawiony), więc musi żyć w `clean()`.
        """
        meta_description = cleaned.get("meta_description") or ""
        if not meta_description:
            # Puste jest w porządku — zadziała fallback na nagłówek.
            return

        length = len(meta_description)
        if length < META_DESCRIPTION_MIN_LENGTH:
            self.add_error(
                "meta_description",
                forms.ValidationError(
                    "Opis SEO ma %(length)d znaków. Dopisz jeszcze co najmniej "
                    "%(missing)d — krótszy opis marnuje miejsce w wynikach wyszukiwania. "
                    "Możesz też zostawić pole puste, wtedy użyjemy nagłówka.",
                    code="meta_description_too_short",
                    params={"length": length, "missing": META_DESCRIPTION_MIN_LENGTH - length},
                ),
            )

    # --- Gotowość do publikacji -------------------------------------------

    def _validate_ready_to_publish(self, cleaned: dict[str, Any]) -> None:
        """Nie wypuszczaj pustej strony pod publiczny adres.

        `headline` jest wymagany bezwarunkowo na poziomie pola modelu
        (`blank=False`) — pusty formularz dostaje błąd (`Meta.error_messages`)
        zanim ten `clean()` się wykona, więc nie duplikujemy tej walidacji
        tutaj. `bio` ma `blank=True` (dopuszczalne w szkicu), więc dopiero
        próba publikacji z pustym `bio` jest błędem — to jedyny przypadek,
        który faktycznie dociera do tego miejsca.
        """
        if cleaned.get("status") != AboutStatus.PUBLISHED:
            return

        missing: list[str] = []
        if not strip_tags(cleaned.get("bio") or "").strip():
            missing.append("biografię")

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

        if cleaned.get("photo") and not (cleaned.get("photo_alt") or "").strip():
            self.add_error(
                "photo_alt",
                forms.ValidationError(
                    "Opisz jednym zdaniem, co widać na zdjęciu. Bez tego osoby "
                    "niewidome nie dowiedzą się, co jest na zdjęciu.",
                    code="missing_photo_alt",
                ),
            )
