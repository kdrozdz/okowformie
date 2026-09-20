"""Serwis generujący treść posta przez LLM (LangChain) i zapisujący ją jako
szkic (`Post` + `PostTranslation`, PL).

Logika biznesowa poza widokiem admina (`ai_content/admin.py`), zgodnie z
`.claude/rules/engineering-principles.md` — widok tylko woła te dwie funkcje
i tłumaczy `PostGenerationError` na `django.contrib.messages.error`.
"""

import logging

from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from langchain.chat_models import init_chat_model

from blog.constants import Language, PostStatus
from blog.models import Post, PostTranslation
from core.sanitization import ALLOWED_TAGS

from .models import AIProviderSettings
from .schemas import GeneratedPostContent

logger = logging.getLogger(__name__)


class PostGenerationError(Exception):
    """Generowanie lub zapis posta się nie powiodły.

    `args[0]` jest gotowym, przyjaznym komunikatem po polsku — widok admina
    przekazuje go wprost do `django.contrib.messages.error`, bez dalszego
    formatowania. Szczegóły techniczne (wyjątek źródłowy, treść błędu
    providera) nigdy nie trafiają do usera, tylko do logu
    (`.claude/rules/security.md`) — patrz `generate_post_content` niżej.
    """


def _build_system_prompt(topic: str, local_focus: str, extra_instructions: str) -> str:
    """Zbuduj prompt sterujący generowaniem `GeneratedPostContent`.

    Allowlista tagów HTML dla `content` pochodzi z `core.sanitization.
    ALLOWED_TAGS` — to jest **egzekwowalna** prawda o tym, co wolno w treści
    posta (używana przy sanityzacji w `PostTranslation.save()`), więc prompt
    ma się do niej dostosować, a nie odwrotnie. Lista kluczy edytora WYSIWYG
    (`blog.models.POST_CONTENT_EXTENSIONS`) opisuje przyciski na pasku
    edytora, nie tagi HTML, jakie produkują — mapowanie 1:1 klucz→tag byłoby
    dla części z nich niejednoznaczne (np. `Typographic`, `History`, `HTML`
    nie odpowiadają żadnemu konkretnemu tagowi). Prompt tylko **kieruje**
    model; treść i tak zostanie zsanityzowana tą samą allowlistą po zapisie,
    więc nawet gdyby model zignorował instrukcję, nic ponad `ALLOWED_TAGS`
    nie przejdzie dalej.

    `extra_instructions` (`AIProviderSettings.extra_instructions`, edytowalne
    w zakładce „Ustawienia AI") doklejane jest na końcu promptu, tylko gdy
    niepuste — persona/ton/wytyczne SEO nie są zaszyte w tym kodzie, redaktor
    może je zmienić albo wyczyścić (`docs/tasks/12-generator-postow-ai.md`,
    sekcja „5a").
    """
    allowed_tags = ", ".join(sorted(ALLOWED_TAGS))
    prompt = (
        "Jesteś redaktorem SEO polskiego bloga optometrycznego (soczewki "
        "kontaktowe, okulary, zdrowie wzroku, porady optyczne). Piszesz "
        "wyłącznie po polsku, rzeczowo i przystępnie dla czytelnika bez "
        "wiedzy medycznej.\n\n"
        f"Temat posta: {topic}\n"
        f"Uwzględnij kontekst lokalny: {local_focus}\n\n"
        "Wygeneruj treść posta zgodną dokładnie z podanym schematem. "
        "Limity długości pól (nie przekraczaj ich):\n"
        "- title: maksymalnie 200 znaków\n"
        "- excerpt: maksymalnie 400 znaków, dwa-trzy zdania streszczenia\n"
        "- meta_title: maksymalnie 60 znaków\n"
        "- meta_description: maksymalnie 160 znaków, najlepiej 150-160\n"
        "- cover_image_alt: maksymalnie 200 znaków, krótki opis okładki\n\n"
        "Pole content to HTML używający wyłącznie następujących tagów: "
        f"{allowed_tags}. Bez <h1> (tytuł strony to osobny nagłówek), bez "
        "<script>, <style>, atrybutów class/style ani żadnego innego tagu "
        "spoza tej listy — i tak zostaną usunięte przy zapisie, więc "
        "używanie ich niczego nie da.\n\n"
        "Pole seo_rationale to krótkie uzasadnienie po polsku, dlaczego "
        "wybrane słowa kluczowe/tytuł/opis SEO są trafne — trafia tylko do "
        "komunikatu w panelu redakcyjnym, nie do treści posta."
    )
    if extra_instructions.strip():
        prompt += f"\n\nDodatkowe wytyczne od redakcji:\n{extra_instructions}"
    return prompt


def generate_post_content(
    *, topic: str, local_focus: str, ai_settings: AIProviderSettings
) -> GeneratedPostContent:
    """Wywołaj skonfigurowanego dostawcę LLM i zwróć structured output.

    Klucz API nigdy nie przechodzi przez ten kod — `init_chat_model` (i SDK
    providera pod spodem) czyta go sam ze zmiennych środowiskowych
    (`ANTHROPIC_API_KEY`/`OPENAI_API_KEY`/`XAI_API_KEY`), zgodnie z decyzją
    w `docs/tasks/12-generator-postow-ai.md`.

    Cały wywołujący fragment jest w jednym `try/except Exception` — LangChain
    nie gwarantuje jednego typu wyjątku na brak klucza, timeout, błąd
    providera czy nieudaną walidację Pydantic wyjścia modelu, więc rozróżnianie
    ich tutaj byłoby fałszywą precyzją. Szczegóły lądują w logu (`.exception`,
    z pełnym tracebackiem); user dostaje jeden, ogólny, bezpieczny komunikat
    po polsku (`.claude/rules/security.md` — treść błędu nigdy do klienta).
    """
    try:
        chat = init_chat_model(
            model=ai_settings.model_name,
            model_provider=ai_settings.provider,
            temperature=ai_settings.temperature,
            max_tokens=ai_settings.max_output_tokens,
            timeout=60,
        )
        structured_chat = chat.with_structured_output(GeneratedPostContent)
        result = structured_chat.invoke(
            _build_system_prompt(topic, local_focus, ai_settings.extra_instructions)
        )

        # `with_structured_output` jest typowany ogólnie jako
        # `Runnable[..., dict[str, Any] | BaseModel]`, bo metoda przyjmuje
        # też schematy niepydantikowe (JSON Schema, TypedDict), dla których
        # zwraca `dict`. Przekazujemy klasę Pydantic (`GeneratedPostContent`),
        # więc w runtime LangChain zawsze zwraca jej instancję — `assert`
        # zamiast `cast`/`type: ignore`, żeby to było też realnym
        # zabezpieczeniem, nie tylko podpowiedzią dla mypy. Umieszczony w
        # `try`, żeby ewentualne złamanie tego założenia (np. przez zmianę
        # API LangChain) trafiło do tej samej ścieżki obsługi błędu, a nie
        # wyleciało jako nieobsłużony `AssertionError`.
        assert isinstance(result, GeneratedPostContent)
    except Exception as exc:
        logger.exception("Generowanie treści posta przez AI nie powiodło się")
        raise PostGenerationError(
            "Nie udało się wygenerować treści posta. Sprawdź konfigurację "
            "dostawcy AI (klucz API w zmiennych środowiskowych, nazwa "
            "modelu) i spróbuj ponownie."
        ) from exc

    return result


def create_draft_post_from_generated_content(
    generated: GeneratedPostContent, *, author: AbstractUser
) -> Post:
    """Zmapuj wygenerowaną treść na `Post` + `PostTranslation` (PL, draft).

    W transakcji: jeśli walidacja tłumaczenia zawiedzie (np. model
    zignorował limit długości mimo instrukcji w promptcie), `Post` też się
    wycofuje — nigdy nie zostaje w bazie osierocony rekord bez tłumaczenia.

    `cover_image` zostaje puste — obrazek nadal wgrywa człowiek, zgodnie z
    decyzją w `docs/tasks/12-generator-postow-ai.md` (sekcja „Decyzje
    wejściowe”, pkt 7).
    """
    try:
        with transaction.atomic():
            post = Post(author=author)
            post.full_clean()
            post.save()

            translation = PostTranslation(
                master=post,
                language_code=Language.PL,
                status=PostStatus.DRAFT,
                title=generated.title,
                excerpt=generated.excerpt,
                content=generated.content,
                meta_title=generated.meta_title,
                meta_description=generated.meta_description,
                cover_image_alt=generated.cover_image_alt,
            )
            # `slug` jest `blank=True` i wypełnia się dopiero w
            # `PostTranslation.save()` (`generate_slug()`) — w tym momencie
            # jest jeszcze puste. Sprawdzone eksperymentalnie: `full_clean()`
            # bez `exclude` na pustym slugu nie wywala się tu błędem
            # unikalności, bo `save()` zawsze uzupełnia slug przed zapisem,
            # więc żaden inny wiersz w bazie nigdy nie ma pustego sluga dla
            # tego samego (master, language_code) — nie ma z czym
            # kolidować. Stąd bez `exclude=["slug"]` (nie dodawaj go bez
            # potwierdzonej potrzeby).
            translation.full_clean()
            translation.save()
    except DjangoValidationError as exc:
        logger.exception("Wygenerowana treść posta nie przeszła walidacji Django")
        raise PostGenerationError(
            "Wygenerowana treść nie przeszła walidacji (np. za długi tytuł "
            "lub opis SEO). Żaden post nie został utworzony — zmień temat i "
            "spróbuj ponownie."
        ) from exc

    return post
