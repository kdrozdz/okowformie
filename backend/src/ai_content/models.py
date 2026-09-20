"""Konfiguracja dostawcy AI: `AIProviderSettings` (singleton) + proxy
`PostGenerator` — druga „twarz” tego samego modelu, zarejestrowana w
adminie pod osobnym `ModelAdmin`, żeby zakładka „Post z AI” mogła
renderować formularz generowania zamiast edycji ustawień.

Wzorowane 1:1 na singletonie `about.models.AboutMe` — ten sam wzorzec
`SINGLETON_ID` + `save()` (`.claude/rules/content-admin.md`).
"""

from typing import Any, ClassVar

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from .constants import AIProvider


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
        help_text="Od 0 (przewidywalnie) do 2 (kreatywnie). Zalecane 0,5–1.",
    )
    max_output_tokens = models.PositiveIntegerField(
        verbose_name="Maks. tokenów wyjścia",
        default=4000,
        validators=[MinValueValidator(1)],
        help_text="Limit długości odpowiedzi modelu. Za niski limit może uciąć treść posta.",
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
