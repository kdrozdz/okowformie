"""Publiczny, read-only widok API brandingu strony (`GET /api/v1/branding/`).

W przeciwieństwie do `about.views.AboutDetailView` ten endpoint **zawsze**
zwraca `200` — nawet gdy `SiteBranding` jeszcze nie istnieje w panelu (świeży
deploy, panel jeszcze pusty). To nie jest zasób z własnym adresem/slugiem,
tylko konfiguracja strony (jak nagłówek), więc pusty stan jest normalną
odpowiedzią, nie błędem (`docs/tasks/11-branding-header.md`) — świadomie inny
wzorzec niż `AboutDetailView`/`Http404`, nie przeoczenie.

Bez `{lang}` w ścieżce (w przeciwieństwie do `blog`/`about`): logo i linki
social media nie są tłumaczone.

Tylko odczyt w fazie 1 (`.claude/rules/security.md`) — brak
`create`/`update`/`delete` tu nie jest przeoczeniem.
"""

from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api import CacheControlMixin

from .models import SiteBranding
from .serializers import SiteBrandingSerializer
from .throttling import BrandingAnonRateThrottle


class SiteBrandingView(CacheControlMixin, APIView):
    """`GET /api/v1/branding/` — pojedynczy obiekt, zawsze `200`."""

    throttle_classes = (BrandingAnonRateThrottle,)

    def get(self, request: Request) -> Response:
        # `or SiteBranding()` (instancja nieutrwalona, `pk=None`) zamiast
        # ręcznie budowanego literalu odpowiedzi — jedno źródło prawdy o
        # kształcie pustego stanu to serializer, nie duplikat w widoku, który
        # mógłby rozjechać się z serializerem przy dodaniu nowego pola
        # (`SiteBrandingSerializer.get_social_links` ma osobny guard na
        # `pk is None`, bo `.social_links.all()` na nieutrwalonej instancji
        # by się wywaliło).
        branding = SiteBranding.objects.prefetch_related("social_links").first() or SiteBranding()
        return Response(SiteBrandingSerializer(branding).data)
