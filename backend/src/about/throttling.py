"""Throttling anonimowych żądań do publicznego API strony „O mnie".

Osobny scope (`about`), nie reużycie `blog.throttling.PostsAnonRateThrottle`
— ten sam powód, dla którego blog ma własny scope zamiast domyślnego `anon`
z DRF-a: pozwala stroić limit tego endpointu niezależnie od innych publicznych
endpointów (`.claude/rules/security.md`: rate limiting publicznego API).
"""

from rest_framework.throttling import AnonRateThrottle


class AboutAnonRateThrottle(AnonRateThrottle):
    scope = "about"
