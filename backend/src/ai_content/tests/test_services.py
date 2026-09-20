"""`_build_system_prompt`, `generate_post_content`, `create_draft_post_from_generated_content`."""

from typing import Any
from unittest.mock import MagicMock

import pytest

from ai_content import services
from ai_content.models import AIProviderSettings
from ai_content.schemas import GeneratedPostContent
from ai_content.services import (
    PostGenerationError,
    _build_system_prompt,
    create_draft_post_from_generated_content,
    generate_post_content,
)
from blog.constants import Language, PostStatus
from blog.models import Post, PostTranslation

pytestmark = pytest.mark.django_db


# --- _build_system_prompt --------------------------------------------------


def test_prompt_zawiera_temat() -> None:
    prompt = _build_system_prompt("Soczewki kontaktowe dla astygmatyków", "Wrocław, Polska", "")

    assert "Soczewki kontaktowe dla astygmatyków" in prompt


def test_prompt_zawiera_fokus_lokalny() -> None:
    prompt = _build_system_prompt("Dobór okularów", "Kraków, Polska", "")

    assert "Kraków, Polska" in prompt


def test_prompt_zawiera_dodatkowe_instrukcje_gdy_niepuste() -> None:
    prompt = _build_system_prompt(
        "Dobór okularów", "Kraków, Polska", "Pisz jak doświadczony optometrysta."
    )

    assert "Pisz jak doświadczony optometrysta." in prompt


def test_prompt_bez_sekcji_dodatkowych_instrukcji_gdy_puste() -> None:
    prompt = _build_system_prompt("Dobór okularów", "Kraków, Polska", "")

    assert "Dodatkowe wytyczne od redakcji" not in prompt


# --- generate_post_content ---------------------------------------------------


def _fake_chat_returning(result: Any) -> MagicMock:
    """Zbuduj fake `chat`: `init_chat_model(...).with_structured_output(...).invoke(...)`."""
    structured_chat = MagicMock()
    structured_chat.invoke.return_value = result
    chat = MagicMock()
    chat.with_structured_output.return_value = structured_chat
    return chat


def test_generate_post_content_zwraca_generated_content_przy_sukcesie(
    monkeypatch: pytest.MonkeyPatch,
    ai_provider_settings: AIProviderSettings,
    mock_generated_content: GeneratedPostContent,
) -> None:
    fake_init_chat_model = MagicMock(return_value=_fake_chat_returning(mock_generated_content))
    monkeypatch.setattr(services, "init_chat_model", fake_init_chat_model)

    result = generate_post_content(
        topic="Soczewki kontaktowe", local_focus="Wrocław, Polska", ai_settings=ai_provider_settings
    )

    assert result == mock_generated_content
    fake_init_chat_model.assert_called_once()


def test_generate_post_content_podnosi_post_generation_error_z_polskim_komunikatem(
    monkeypatch: pytest.MonkeyPatch, ai_provider_settings: AIProviderSettings
) -> None:
    def _boom(*args: Any, **kwargs: Any) -> Any:
        raise RuntimeError("boom")

    monkeypatch.setattr(services, "init_chat_model", _boom)

    with pytest.raises(PostGenerationError) as exc_info:
        generate_post_content(
            topic="Soczewki kontaktowe",
            local_focus="Wrocław, Polska",
            ai_settings=ai_provider_settings,
        )

    message = str(exc_info.value)
    assert "Nie udało się wygenerować treści posta" in message
    # Komunikat dla usera nie może zdradzać szczegółów wyjątku źródłowego.
    assert "boom" not in message


# --- create_draft_post_from_generated_content --------------------------------


def test_create_draft_post_mapuje_pola_na_post_i_translation(
    author: Any, mock_generated_content: GeneratedPostContent
) -> None:
    post = create_draft_post_from_generated_content(mock_generated_content, author=author)

    assert post.author_id == author.pk
    translation = PostTranslation.objects.get(master=post, language_code=Language.PL)
    assert translation.status == PostStatus.DRAFT
    assert translation.language_code == Language.PL
    assert translation.title == mock_generated_content.title
    assert translation.excerpt == mock_generated_content.excerpt
    assert translation.content == mock_generated_content.content
    assert translation.meta_title == mock_generated_content.meta_title
    assert translation.meta_description == mock_generated_content.meta_description
    assert translation.cover_image_alt == mock_generated_content.cover_image_alt
    assert translation.slug != ""


def test_create_draft_post_sanityzuje_wstrzykniety_tag_script(author: Any) -> None:
    """Treść wygenerowana przez LLM to wciąż niezaufane wejście — nawet gdyby
    model zignorował instrukcję o dozwolonych tagach (`_build_system_prompt`),
    zapis przez `PostTranslation.save()` (`.claude/rules/security.md`) ma
    usunąć `<script>` niezależnie od tej ścieżki wywołania, tak samo jak przy
    zapisie z panelu redakcyjnego."""
    malicious = GeneratedPostContent(
        title="Soczewki kontaktowe",
        excerpt="Zajawka",
        content='<p>Bezpieczny akapit</p><script>alert("xss")</script>',
        meta_title="Tytuł SEO",
        meta_description="Opis SEO",
        cover_image_alt="Alt okładki",
        seo_rationale="Uzasadnienie",
    )

    post = create_draft_post_from_generated_content(malicious, author=author)

    translation = PostTranslation.objects.get(master=post, language_code=Language.PL)
    assert "<script" not in translation.content
    assert "<p>Bezpieczny akapit</p>" in translation.content


def test_create_draft_post_usuwa_handler_onerror(author: Any) -> None:
    """Analogicznie do `<script>`, ale dla atrybutu `onerror` (XSS przez
    handler zdarzenia na dozwolonym tagu `<img>`, nie przez zabroniony tag)."""
    malicious = GeneratedPostContent(
        title="Soczewki kontaktowe",
        excerpt="Zajawka",
        content='<img src="x.jpg" onerror="alert(1)" alt="Opis">',
        meta_title="Tytuł SEO",
        meta_description="Opis SEO",
        cover_image_alt="Alt okładki",
        seo_rationale="Uzasadnienie",
    )

    post = create_draft_post_from_generated_content(malicious, author=author)

    translation = PostTranslation.objects.get(master=post, language_code=Language.PL)
    assert "onerror" not in translation.content
    assert 'alt="Opis"' in translation.content


def test_create_draft_post_z_za_dlugim_polem_podnosi_blad_i_nie_zostawia_posta(author: Any) -> None:
    # `model_construct` omija walidację Pydantic — symuluje model LLM, który
    # zignorował limit długości mimo instrukcji w promptcie.
    too_long = GeneratedPostContent.model_construct(
        title="a" * 500,
        excerpt="Zajawka",
        content="<p>Treść</p>",
        meta_title="Tytuł SEO",
        meta_description="Opis SEO",
        cover_image_alt="Alt okładki",
        seo_rationale="Uzasadnienie",
    )

    with pytest.raises(PostGenerationError):
        create_draft_post_from_generated_content(too_long, author=author)

    assert Post.objects.count() == 0
    assert PostTranslation.objects.count() == 0
