"""Elementy współdzielone przez publiczne, read-only widoki API domen treści.

Wydzielone z `blog.views` (`docs/decisions/2026-09-19-model-about-me.md`):
`LanguageURLKwargMixin` i `CacheControlMixin` nie mają nic wspólnego z
postami — dotyczą tego, że każdy publiczny endpoint API bierze język z URL-a
i ma dostać ten sam nagłówek `Cache-Control`. `about` korzysta z nich wprost,
bez zależności od `blog` (`.claude/rules/scope.md`: apps podzielone domenowo).
"""

from typing import Any
from urllib.parse import urljoin, urlparse

from django.conf import settings
from django.http import Http404
from rest_framework.request import Request
from rest_framework.response import Response

from .constants import Language

#: Domyślny `Cache-Control` dla publicznych endpointów read-only. Dostawca
#: CDN nierozstrzygnięty (poza zakresem), ale sam nagłówek od niego nie
#: zależy (`.claude/rules/performance.md`).
DEFAULT_CACHE_CONTROL = "public, max-age=60"


def absolute_media_url(url: str) -> str:
    """Buduj absolutny URL obrazu z `settings.SITE_URL`, nie z `Host` żądania.

    Współdzielone przez `about` i `blog` (`photo`/`certificate.image`/
    `cover_image` w ich serializerach) — bez tego każda domena budowałaby
    ten sam URL po swojemu, co jest dokładnie duplikacją zabronioną w
    `.claude/rules/scope.md`.

    Celowo NIE `request.build_absolute_uri()`: ten helper bierze host z
    nagłówka `Host` PRZYCHODZĄCEGO żądania, a żądania do API bywają wołane
    server-side z innego kontenera/adresu niż publiczna domena (np. frontend
    Next.js łączący się przez `http://backend:8000` wewnątrz sieci docker
    compose) — wtedy `og:image`/JSON-LD dostałyby wewnętrzny, nieosiągalny
    z zewnątrz adres zamiast publicznego.

    `url` z `ImageField.url` jest ścieżką względną przy obecnym
    `FileSystemStorage` — ale storage mediów to otwarta decyzja
    (`CLAUDE.md`), a `STORAGES` Django pozwala go podmienić bez zmiany kodu
    (`.claude/rules/scope.md`). Backend typu S3 (`django-storages` itp.)
    zwraca z `.url` już absolutny URL do własnej domeny (bucket/CDN) — w tym
    wypadku `SITE_URL` byłby błędny i nie powinien być doklejany.
    """

    if urlparse(url).scheme:
        return url
    return urljoin(settings.SITE_URL, url)


class LanguageURLKwargMixin:
    """Waliduje `lang` z URL-a — nieobsługiwany kod języka to 404, nie 400.

    Zły `lang` jest traktowany tak samo jak nieistniejący zasób.
    """

    kwargs: dict[str, Any]

    def get_language_code(self) -> str:
        language_code = self.kwargs["lang"]
        if language_code not in Language.values:
            raise Http404(f"Unsupported language: {language_code!r}.")
        return language_code


class CacheControlMixin:
    """Dokłada `Cache-Control` do udanych odpowiedzi.

    Błędy (404/429) nie są cache'owane — nagłówek dotyczy tylko treści,
    którą warto trzymać przed API (`.claude/rules/performance.md`).
    """

    #: Nadpisywalne w podklasie, gdyby konkretny endpoint chciał inny czas cache.
    cache_control: str = DEFAULT_CACHE_CONTROL

    def finalize_response(
        self, request: Request, response: Response, *args: Any, **kwargs: Any
    ) -> Response:
        response = super().finalize_response(request, response, *args, **kwargs)  # type: ignore[misc]
        if response.status_code == 200:
            response["Cache-Control"] = self.cache_control
        return response
