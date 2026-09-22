"""Stałe domenowe generatora treści AI."""

from django.db import models


class AIProvider(models.TextChoices):
    """Dostawcy LLM obsługiwani przez `init_chat_model` (LangChain).

    Wartości są celowo identyczne ze stringami `model_provider` oczekiwanymi
    przez `langchain.chat_models.init_chat_model` — nie zmieniaj ich bez
    sprawdzenia zgodności z LangChain, bo to jest jedyny sposób, w jaki
    `ai_content.services` mówi LangChainowi, którego SDK użyć.
    """

    ANTHROPIC = "anthropic", "Anthropic (Claude)"
    OPENAI = "openai", "OpenAI (GPT)"
    XAI = "xai", "xAI (Grok)"
