"""Throttling anonimowych żądań do publicznego API plików do pobrania."""

from rest_framework.throttling import AnonRateThrottle


class DownloadsAnonRateThrottle(AnonRateThrottle):
    """Osobny scope (`downloads`), ten sam powód co
    `blog.throttling.PostsAnonRateThrottle`: pozwala stroić limit tego
    endpointu niezależnie od innych publicznych endpointów
    (`.claude/rules/security.md`: rate limiting publicznego API).
    """

    scope = "downloads"
