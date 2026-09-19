"""Throttling anonimowych żądań do publicznego API bloga."""

from rest_framework.throttling import AnonRateThrottle


class PostsAnonRateThrottle(AnonRateThrottle):
    """Osobny scope (`posts`) zamiast domyślnego `anon` z DRF-a.

    Nazwany scope pozwala w przyszłości stroić limit publicznego API bloga
    niezależnie od innych publicznych endpointów faz 2/3
    (`.claude/rules/security.md`: rate limiting dla publicznego API), bez
    dzielenia budżetu żądań z endpointami, których jeszcze nie ma.
    """

    scope = "posts"
