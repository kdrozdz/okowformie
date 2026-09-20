"""Singleton `AIProviderSettings` + proxy `PostGenerator` dzielący tabelę."""

from typing import Any

import pytest

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
