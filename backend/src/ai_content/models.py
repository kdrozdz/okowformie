"""Konfiguracja dostawcy AI: `AIProviderSettings` (singleton) + proxy
`PostGenerator` — druga „twarz” tego samego modelu, zarejestrowana w
adminie pod osobnym `ModelAdmin`, żeby zakładka „Post z AI” mogła
renderować formularz generowania zamiast edycji ustawień.

Wzorowane 1:1 na singletonie `about.models.AboutMe` — ten sam wzorzec
`SINGLETON_ID` + `save()` (`.claude/rules/content-admin.md`).
"""

from typing import Any, ClassVar

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from .constants import AIProvider

#: Anthropic (Claude) odrzuca `temperature` powyżej 1 na poziomie API — inni
#: obsługiwani dostawcy (OpenAI, xAI) akceptują do 2. Walidator pola
#: (`MaxValueValidator`) musi zostać przy 2, żeby nie blokować redaktora
#: zmieniającego providera na jeden z pozostałych dwóch; ten dodatkowy limit
#: obowiązuje tylko w kombinacji z `AIProvider.ANTHROPIC` — patrz `clean()`.
ANTHROPIC_MAX_TEMPERATURE = 1


class AIProviderSettings(models.Model):
    """Konfiguracja dostawcy LLM używanego do generowania postów.

    Zwykły model, **nie** `TranslatableModel` — konfiguracja dostawcy jest
    niezależna od języka treści, którą generuje (`docs/tasks/
    12-generator-postow-ai.md`, sekcja „Decyzje wejściowe”). Singleton:
    zawsze dokładnie jeden rekord (`pk=1`), tak jak `AboutMe` — jeden blog,
    jedna aktywna konfiguracja dostawcy naraz.
    """

    #: Jedyny dozwolony klucz główny. `AIProviderSettingsAdmin.has_add_permission`
    #: blokuje próbę utworzenia drugiego rekordu z panelu; `save()` niżej
    #: pilnuje tego samego niezmiennika dla dowolnej innej ścieżki zapisu.
    SINGLETON_ID: ClassVar[int] = 1

    provider = models.CharField(
        verbose_name="Dostawca",
        max_length=16,
        choices=AIProvider.choices,
        default=AIProvider.ANTHROPIC,
        help_text="Firma, której model językowy generuje treść posta.",
    )
    model_name = models.CharField(
        verbose_name="Nazwa modelu",
        max_length=100,
        help_text=(
            "Dokładna nazwa modelu u wybranego dostawcy, np. „claude-sonnet-4-5”. "
            "Celowo bez listy do wyboru — dostawcy dodają i zmieniają nazwy "
            "modeli częściej, niż wychodzą nowe wersje tego panelu."
        ),
    )
    temperature = models.FloatField(
        verbose_name="Temperatura",
        default=0.7,
        validators=[MinValueValidator(0), MaxValueValidator(2)],
        help_text=(
            "Od 0 (przewidywalnie) do 2 (kreatywnie) — dla Anthropic maksimum to 1. "
            "Zalecane 0,5–1."
        ),
    )
    max_output_tokens = models.PositiveIntegerField(
        verbose_name="Maks. tokenów wyjścia",
        default=4000,
        validators=[MinValueValidator(1)],
        help_text="Limit długości odpowiedzi modelu. Za niski limit może uciąć treść posta.",
    )
    extra_instructions = models.TextField(
        verbose_name="Dodatkowe instrukcje dla AI",
        blank=True,
        default=(
            "Pisz jak doświadczony optometrysta — rzeczowo, z autorytetem. "
            "Stosuj sprawdzone zasady SEO: jasna struktura nagłówków, odpowiedź "
            "na intencję wyszukiwania, zasady E-E-A-T."
        ),
        help_text=(
            "Doklejane do promptu przy każdym generowaniu — persona, ton, "
            "wytyczne SEO. Możesz zostawić puste albo zmienić na własne."
        ),
    )

    class Meta:
        verbose_name = "Ustawienia AI"
        verbose_name_plural = "Ustawienia AI"

    def __str__(self) -> str:
        if not self.model_name:
            return self.get_provider_display()
        return f"{self.get_provider_display()} — {self.model_name}"

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Singleton: bez względu na to, co przyjdzie, wiersz ląduje pod `pk=1`.

        Ten sam wzorzec co `about.models.AboutMe.save()`.
        """
        self.pk = self.SINGLETON_ID
        super().save(*args, **kwargs)

    def clean(self) -> None:
        """Walidacja krzyżowa `provider`+`temperature`.

        `MaxValueValidator(2)` na polu `temperature` sam w sobie nie wystarcza
        — jest poprawny dla OpenAI/xAI, ale Anthropic odrzuca wartości >1 na
        poziomie API, dopiero przy wywołaniu LLM w `ai_content.services.
        generate_post_content` (złapane przez generyczny `except Exception`,
        z komunikatem, który nigdy nie wspomina o temperaturze). `clean()`
        łapie to wcześniej, przy `full_clean()` — w adminie i wszędzie indziej.
        """
        super().clean()
        if self.provider == AIProvider.ANTHROPIC and self.temperature > ANTHROPIC_MAX_TEMPERATURE:
            raise ValidationError(
                {
                    "temperature": (
                        "Anthropic (Claude) akceptuje temperaturę tylko od 0 do 1. "
                        "Zmniejsz wartość albo wybierz innego dostawcę."
                    )
                }
            )


class PostGenerator(AIProviderSettings):
    """Proxy model — ta sama tabela co `AIProviderSettings`, druga rejestracja
    w adminie pod inną nazwą i innym `ModelAdmin` (formularz generowania
    zamiast edycji konfiguracji, patrz `ai_content/admin.py`).

    Bez własnej tabeli w bazie (`proxy = True`) — to tylko inna „twarz”
    tego samego rekordu do celów UI panelu.
    """

    class Meta:
        proxy = True
        verbose_name = "Post z AI"
        verbose_name_plural = "Post z AI"
        #: Bez domyślnych `add/change/delete/view_postgenerator` — dostęp do
        #: zakładki „Post z AI" jest kontrolowany przez `blog.add_post`
        #: + `blog.change_post` (`PostGeneratorAdmin._can_generate`), nigdy
        #: przez uprawnienia tego modelu. Bez tej opcji Django tworzyłoby
        #: cztery uprawnienia, których żaden kod nigdy nie sprawdza — superuser
        #: nadający `ai_content.view_postgenerator` przez standardowy panel
        #: Użytkownicy/Grupy dostałby złudzenie kontroli nad dostępem, które
        #: nic nie robi. Ten sam wzorzec co `blog.models.PostTranslation.Meta`
        #: i `about.models.AboutMeTranslation.Meta`.
        default_permissions = ()
