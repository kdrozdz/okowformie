"""Formularz panelu redakcyjnego.

Cała walidacja mówi po polsku i mówi **co zrobić**, nie co się zepsuło
(`.claude/rules/content-admin.md`). Komunikaty są tutaj, a nie w modelu,
bo to warstwa rozmowy z redaktorem; model pilnuje niezmienników twardo
(ograniczenia bazy, sanityzacja w `save()`).
"""

from typing import Any

from django import forms
from django.utils.html import strip_tags
from django_prose_editor.widgets import AdminProseEditorWidget
from parler.forms import TranslatableModelForm

from core.i18n import language_label

from .constants import META_DESCRIPTION_MIN_LENGTH, PostStatus
from .models import Post, PostTranslation
from .slugs import build_unique_slug


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
            # Domyślny `TextInput` był węższy niż `cover_image_alt` mimo
            # podobnej długości treści (tytuł/opis SEO, do 60/160 znaków) —
            # niespójność, nie świadomy wybór (`docs/tasks/
            # 15-motyw-panelu-admina.md`).
            "meta_title": forms.TextInput(attrs={"size": 80}),
            "meta_description": forms.Textarea(attrs={"rows": 3}),
            # Wariant widgetu dopasowany stylami do panelu. Parler buduje
            # pola tłumaczone poza `formfield_overrides` admina, więc admin
            # sam by go nie podmienił.
            "content": AdminProseEditorWidget,
        }
        # Django odrzuca `title`/`excerpt` puste i `meta_title`/`meta_description`
        # za długie na poziomie pola formularza — **przed** `clean()` niżej —
        # więc przyjazny komunikat musi siedzieć tutaj, nie w
        # `_validate_seo`/`_validate_ready_to_publish` (te gałęzie były martwe:
        # `cleaned_data` nie zawiera już odrzuconej wartości, kiedy tamten kod
        # by się wykonał). Ten sam wzorzec co `about.forms.AboutMeAdminForm.Meta`
        # — patrz tam komentarz o `django-parler` i o tym, dlaczego
        # `error_messages` na polu modelu by tu nie zadziałał.
        error_messages = {
            "title": {
                "required": "Tytuł jest wymagany — bez niego post nie ma nagłówka.",
            },
            "excerpt": {
                "required": (
                    "Zajawka jest wymagana — bez niej post nie pokaże się poprawnie "
                    "na liście. Napisz dwa–trzy zdania streszczenia."
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
        self._validate_slug_free(cleaned)
        self._validate_seo(cleaned)
        self._validate_ready_to_publish(cleaned)
        self._warn_if_cover_image_will_be_lost()
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
        """Za długie `meta_title`/`meta_description` są już odrzucane na
        poziomie pola formularza (`Meta.error_messages`, klucz `max_length`)
        — Django woła `run_validators()` zanim ten `clean()` w ogóle się
        wykona. Jedyna gałąź, która faktycznie dociera tutaj, to „za krótki
        opis SEO": to reguła biznesowa bez odpowiednika w polu modelu
        (`min_length` nie jest tam ustawiony), więc musi żyć w `clean()`.
        """
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

    # --- Gotowość do publikacji -------------------------------------------

    def _validate_ready_to_publish(self, cleaned: dict[str, Any]) -> None:
        """Nie wypuszczaj pustej strony pod publiczny adres.

        `title`/`excerpt` są wymagane bezwarunkowo na poziomie pola modelu
        (`blank=False`) — pusty formularz dostaje błąd (`Meta.error_messages`)
        zanim ten `clean()` się wykona, więc nie duplikujemy tej walidacji
        tutaj. `content` ma `blank=True` (dopuszczalne w szkicu), więc dopiero
        próba publikacji z pustą treścią jest błędem — to jedyny przypadek,
        który faktycznie dociera do tego miejsca.
        """
        if cleaned.get("status") != PostStatus.PUBLISHED:
            return

        missing: list[str] = []
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

    # --- Utrata wybranego obrazu przy błędzie formularza -----------------

    def _warn_if_cover_image_will_be_lost(self) -> None:
        """Ostrzeż, gdy błąd gdziekolwiek indziej na formularzu skasuje wybrany obraz.

        Przeglądarka nie potrafi ponownie wypełnić `<input type="file">` po
        przeładowaniu strony z błędem walidacji — to ograniczenie HTML, nie
        coś, co da się naprawić w Django. Obraz wybrany w tym samym żądaniu,
        w którym walidacja czegokolwiek innego się nie powiodła, zniknie z
        formularza po jego ponownym pokazaniu. Bez tego ostrzeżenia redaktor
        poprawia zgłoszony błąd, zapisuje ponownie i dostaje post bez
        okładki, nie wiedząc, że musi wybrać plik jeszcze raz — dokładnie
        tak zniknęła okładka na poście „agata".

        Pomijamy przypadek, gdy błąd dotyczy samego `cover_image` (np. zły
        format) — ten błąd już mówi, co poprawić przed ponownym wyborem
        pliku, więc drugi, generyczny komunikat na tym samym polu tylko by
        mylił.
        """
        if "cover_image" not in self.files:
            return
        if "cover_image" in self._errors or not self._errors:
            return

        self.add_error(
            "cover_image",
            forms.ValidationError(
                "Ten obraz nie zapisze się razem z poprawką błędów poniżej — "
                "przeglądarka nie zapamiętuje wybranego pliku. Popraw błędy, "
                "wybierz go jeszcze raz i dopiero wtedy zapisz.",
                code="cover_image_lost_on_resubmit",
            ),
        )
