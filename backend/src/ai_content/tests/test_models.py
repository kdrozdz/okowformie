"""Singleton `AIProviderSettings` + proxy `PostGenerator` dzielący tabelę."""

from typing import Any

import pytest
from django.core.exceptions import ValidationError

from ai_content.constants import AIProvider
from ai_content.models import AIProviderSettings, PostGenerator

pytestmark = pytest.mark.django_db


def test_save_wymusza_pk_1_niezaleznie_od_przekazanej_wartosci(db: Any) -> None:
    settings_obj = AIProviderSettings(
        pk=999,
        provider=AIProvider.OPENAI,
        model_name="gpt-test",
        temperature=1.0,
        max_output_tokens=2000,
    )

    settings_obj.save()

    assert settings_obj.pk == AIProviderSettings.SINGLETON_ID
    assert AIProviderSettings.objects.count() == 1


def test_kolejny_zapis_nadpisuje_ten_sam_wiersz_zamiast_tworzyc_drugi(db: Any) -> None:
    AIProviderSettings.objects.create(
        provider=AIProvider.ANTHROPIC,
        model_name="claude-a",
        temperature=0.5,
        max_output_tokens=1000,
    )
    AIProviderSettings(
        provider=AIProvider.XAI, model_name="grok-b", temperature=0.9, max_output_tokens=8000
    ).save()

    assert AIProviderSettings.objects.count() == 1
    only = AIProviderSettings.objects.get()
    assert only.provider == AIProvider.XAI
    assert only.model_name == "grok-b"


def test_post_generator_dzieli_tabele_z_ai_provider_settings(db: Any) -> None:
    settings_obj = AIProviderSettings.objects.create(
        provider=AIProvider.ANTHROPIC,
        model_name="claude-test",
        temperature=0.7,
        max_output_tokens=4000,
    )

    assert PostGenerator.objects.filter(pk=settings_obj.pk).exists()
    via_proxy = PostGenerator.objects.get(pk=settings_obj.pk)
    assert via_proxy.model_name == "claude-test"


def test_zapis_przez_proxy_jest_widoczny_przez_model_bazowy(db: Any) -> None:
    generator = PostGenerator(
        provider=AIProvider.OPENAI, model_name="gpt-proxy", temperature=0.3, max_output_tokens=500
    )
    generator.save()

    assert AIProviderSettings.objects.filter(pk=generator.pk, model_name="gpt-proxy").exists()


# --- Walidatory zakresu (`temperature`, `max_output_tokens`) ----------------


@pytest.mark.parametrize("temperature", [-0.1, 2.1])
def test_temperatura_poza_zakresem_0_2_jest_odrzucana_przez_full_clean(
    db: Any, temperature: float
) -> None:
    """`temperature` ma sens tylko w [0, 2] (`MinValueValidator(0)`,
    `MaxValueValidator(2)`) — wartość spoza tego zakresu nie jest tym, czego
    oczekuje żaden SDK providera LangChain."""
    settings_obj = AIProviderSettings(
        provider=AIProvider.ANTHROPIC,
        model_name="claude-test",
        temperature=temperature,
        max_output_tokens=4000,
    )

    with pytest.raises(ValidationError) as error:
        settings_obj.full_clean()

    assert "temperature" in error.value.message_dict


@pytest.mark.parametrize(
    ("temperature", "provider"),
    [
        (0, AIProvider.ANTHROPIC),
        (1, AIProvider.ANTHROPIC),  # granica dodatkowego limitu Anthropic, patrz niżej
        (2, AIProvider.OPENAI),  # granica pola (`MaxValueValidator(2)`) dla dostawcy bez limitu 1
    ],
)
def test_temperatura_na_granicy_zakresu_jest_akceptowana(
    db: Any, temperature: float, provider: AIProvider
) -> None:
    settings_obj = AIProviderSettings(
        provider=provider,
        model_name="claude-test",
        temperature=temperature,
        max_output_tokens=4000,
    )

    settings_obj.full_clean()  # nie powinno podnieść ValidationError


# --- Walidacja krzyżowa provider+temperature (Anthropic <= 1) --------------


def test_temperatura_powyzej_1_dla_anthropic_jest_odrzucana_przez_clean(db: Any) -> None:
    """Anthropic (Claude) odrzuca `temperature` > 1 na poziomie API, mimo że
    pole samo w sobie dopuszcza do 2 (`MaxValueValidator(2)`) — dla OpenAI/xAI.
    `AIProviderSettings.clean()` łapie to wcześniej, przy `full_clean()`."""
    settings_obj = AIProviderSettings(
        provider=AIProvider.ANTHROPIC,
        model_name="claude-test",
        temperature=1.5,
        max_output_tokens=4000,
    )

    with pytest.raises(ValidationError) as error:
        settings_obj.full_clean()

    assert "temperature" in error.value.message_dict
    assert "Anthropic" in error.value.message_dict["temperature"][0]


@pytest.mark.parametrize("provider", [AIProvider.OPENAI, AIProvider.XAI])
def test_temperatura_powyzej_1_dla_innych_dostawcow_jest_akceptowana(
    db: Any, provider: AIProvider
) -> None:
    """Limit dodatkowy (<=1) dotyczy wyłącznie Anthropic — OpenAI/xAI akceptują
    do 2, zgodnie z walidatorem pola."""
    settings_obj = AIProviderSettings(
        provider=provider,
        model_name="model-test",
        temperature=1.5,
        max_output_tokens=4000,
    )

    settings_obj.full_clean()  # nie powinno podnieść ValidationError


def test_max_output_tokens_ponizej_1_jest_odrzucany_przez_full_clean(db: Any) -> None:
    """`max_output_tokens` musi być dodatni (`MinValueValidator(1)`) — `0` albo
    ujemna wartość oznaczałaby wywołanie LLM z limitem, który nic nie zwróci."""
    settings_obj = AIProviderSettings(
        provider=AIProvider.ANTHROPIC,
        model_name="claude-test",
        temperature=0.7,
        max_output_tokens=0,
    )

    with pytest.raises(ValidationError) as error:
        settings_obj.full_clean()

    assert "max_output_tokens" in error.value.message_dict
