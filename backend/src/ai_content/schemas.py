"""Pydantic schema wymuszający structured output z LLM.

`GeneratedPostContent` to kontrakt między promptem (`ai_content.services.
_build_system_prompt`) a `langchain...with_structured_output(...)` — model
językowy musi zwrócić dokładnie te pola, w tym kształcie.

Limity długości są celowo przepisane 1:1 z `blog.models.PostTranslation`
(`title`, `excerpt`, `cover_image_alt`) i `core.constants`
(`META_TITLE_MAX_LENGTH`, `META_DESCRIPTION_MAX_LENGTH`) — to jedno źródło
prawdy o docelowych limitach pól Django, tylko przeniesione ręcznie na
granicę Pydantic/LangChain, bo nie da się tego zaimportować wprost: Pydantic
`Field(max_length=...)` i Django `CharField(max_length=...)` to dwa różne
mechanizmy walidacji w dwóch różnych warstwach. Zgodność między nimi pilnuje
review, nie import — jeśli limit w `blog.models`/`core.constants` się
zmieni, trzeba też zmienić go tutaj.

Te limity łapią przesadzone wyjście modelu już tu, zanim trafi do
`create_draft_post_from_generated_content` — `full_clean()` na
`PostTranslation` i tak zweryfikuje je ponownie (Django nie ufa temu, co
przyszło z innej warstwy), ale błąd Pydantic jest tańszy i ma czytelniejszy
komunikat niż `django.core.exceptions.ValidationError` z głębi `full_clean()`.
"""

import pydantic


class GeneratedPostContent(pydantic.BaseModel):
    """Treść posta wygenerowana przez LLM, gotowa do zmapowania na `Post`."""

    title: str = pydantic.Field(
        ..., max_length=200, description="Tytuł posta — widoczny na liście i jako H1."
    )
    excerpt: str = pydantic.Field(
        ..., max_length=400, description="Dwa-trzy zdania zajawki, widoczne na liście postów."
    )
    content: str = pydantic.Field(
        ...,
        description=(
            "Treść posta jako HTML zbudowany wyłącznie z dozwolonych tagów "
            "(patrz allowlista w promptcie). Bez limitu długości — długość "
            "artykułu pilnuje `max_output_tokens` konfiguracji dostawcy, nie "
            "ten schemat."
        ),
    )
    meta_title: str = pydantic.Field(
        ..., max_length=60, description="Tytuł SEO (meta title) — krótszy niż tytuł posta."
    )
    meta_description: str = pydantic.Field(
        ..., max_length=160, description="Opis SEO (meta description), najlepiej 150-160 znaków."
    )
    cover_image_alt: str = pydantic.Field(
        ...,
        max_length=200,
        description="Opis alternatywny okładki — obrazek doda redaktor ręcznie.",
    )
    seo_rationale: str = pydantic.Field(
        ...,
        description=(
            "Krótkie uzasadnienie wyboru słów kluczowych/tytułu/opisu SEO, po "
            "polsku. Tylko do komunikatu w panelu admina — nigdy nie trafia "
            "do bazy."
        ),
    )
