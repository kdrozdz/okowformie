"""Throttling anonimowych żądań do publicznego API brandingu strony.

Osobny scope (`branding`), nie reużycie `about.throttling.AboutAnonRateThrottle`
ani `blog.throttling.PostsAnonRateThrottle` — ten sam powód, dla którego każdy
publiczny endpoint ma własny scope: pozwala stroić limit niezależnie od
innych endpointów (`.claude/rules/security.md`: rate limiting publicznego API).
"""

from rest_framework.throttling import AnonRateThrottle


class BrandingAnonRateThrottle(AnonRateThrottle):
    scope = "branding"
