"""Formularz zakładki „Post z AI".

Zwykły `forms.Form`, nie `ModelForm` — nie ma modelu do wypełnienia, dane
trafiają do `ai_content.services.generate_post_content` jako argumenty,
zanim jakikolwiek `Post`/`PostTranslation` w ogóle powstanie. Komunikaty po
polsku, mówiące **co zrobić**, ten sam wzorzec co `about.forms.AboutMeAdminForm`
(`.claude/rules/content-admin.md`).
"""

from django import forms


class PostGenerationForm(forms.Form):
    """Temat i fokus lokalny — jedyny wkład redaktora do generowania posta."""

    topic = forms.CharField(
        label="Temat posta",
        max_length=200,
        error_messages={
            "required": "Temat jest wymagany — bez niego AI nie wie, o czym napisać.",
            "max_length": (
                "Temat ma %(show_value)d znaków, maksimum to %(limit_value)d. Skróć go do "
                "głównej myśli — szczegóły dopisze AI."
            ),
        },
    )
    local_focus = forms.CharField(
        label="Fokus lokalny",
        max_length=200,
        initial="Wrocław, Polska",
        error_messages={
            "required": (
                "Fokus lokalny jest wymagany — mówi AI, dla jakiego regionu pisze poradę."
            ),
            "max_length": (
                "Fokus lokalny ma %(show_value)d znaków, maksimum to %(limit_value)d. Skróć go."
            ),
        },
    )
