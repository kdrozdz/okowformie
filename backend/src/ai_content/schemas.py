"""Pydantic schema wymuszający structured output z LLM.

`GeneratedPostContent` to kontrakt między promptem (`ai_content.services.
_build_system_prompt`/`_build_user_prompt`) a `langchain...
with_structured_output(...)` — model językowy musi zwrócić dokładnie te
pola, w tym kształcie.

Limity długości pochodzą z jednego źródła prawdy zamiast literałów przepisanych
ręcznie w dwóch miejscach: `meta_title`/`meta_description` z `core.constants`
(neutralna domenowo, bez modeli — bezpieczny import stąd), `title`/`excerpt`/
`cover_image_alt` odczytane raz przy imporcie tego modułu wprost z pól
`blog.models.PostTranslation` (`Field.max_length`, ten sam wzorzec co
`PostTranslation.generate_slug()`). Jeśli limit w `blog.models`/
`core.constants` się zmieni, ten moduł zmienia się razem z nim — nic nie
trzeba pilnować ręcznie przy review.

Te limity łapią przesadzone wyjście modelu już tu, zanim trafi do
`create_draft_post_from_generated_content` — `full_clean()` na
`PostTranslation` i tak zweryfikuje je ponownie (Django nie ufa temu, co
przyszło z innej warstwy), ale błąd Pydantic jest tańszy i ma czytelniejszy
komunikat niż `django.core.exceptions.ValidationError` z głębi `full_clean()`.
"""

import pydantic

from blog.models import PostTranslation
from core.constants import META_DESCRIPTION_MAX_LENGTH, META_TITLE_MAX_LENGTH

#: `int` mimo że `Field.max_length` jest typowane jako `int | None` — te
#: konkretne pola `PostTranslation` zawsze mają `max_length` ustawiony
#: (`CharField` z wprost podanym limitem), stąd `# type: ignore[assignment]`
#: zamiast `assert`/`cast`, ten sam wzorzec co
#: `blog.models.PostTranslation.generate_slug`.
TITLE_MAX_LENGTH: int = PostTranslation._meta.get_field("title").max_length  # type: ignore[assignment]
EXCERPT_MAX_LENGTH: int = PostTranslation._meta.get_field("excerpt").max_length  # type: ignore[assignment]
COVER_IMAGE_ALT_MAX_LENGTH: int = PostTranslation._meta.get_field(  # type: ignore[assignment]
    "cover_image_alt"
).max_length


class GeneratedPostContent(pydantic.BaseModel):
    """Treść posta wygenerowana przez LLM, gotowa do zmapowania na `Post`."""

    title: str = pydantic.Field(
        ..., max_length=TITLE_MAX_LENGTH, description="Tytuł posta — widoczny na liście i jako H1."
    )
    excerpt: str = pydantic.Field(
        ...,
        max_length=EXCERPT_MAX_LENGTH,
        description="Dwa-trzy zdania zajawki, widoczne na liście postów.",
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
        ...,
        max_length=META_TITLE_MAX_LENGTH,
        description="Tytuł SEO (meta title) — krótszy niż tytuł posta.",
    )
    meta_description: str = pydantic.Field(
        ...,
        max_length=META_DESCRIPTION_MAX_LENGTH,
        description="Opis SEO (meta description), najlepiej 150-160 znaków.",
    )
    cover_image_alt: str = pydantic.Field(
        ...,
        max_length=COVER_IMAGE_ALT_MAX_LENGTH,
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
