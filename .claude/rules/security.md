---
paths:
  - "backend/**"
  - "frontend/**"
  - "infra/**"
  - ".github/**"
  - "docker-compose*.yml"
---

# Bezpieczeństwo

- `DEBUG=False` poza dev; `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `CORS_ALLOWED_ORIGINS` jawne, bez wildcardów.
- Panel admina pod niestandardowym URL-em; docelowo 2FA dla kont staff.
- HTML z edytora **sanityzowany po stronie backendu** (allowlist tagów, np. `nh3`/`bleach`) — nigdy nie renderuj surowego HTML z bazy bez sanityzacji. Sanityzuj przy zapisie **i** przy serializacji; `dangerouslySetInnerHTML` tylko na treści, która przeszła backendową allowlistę.
- Upload plików: walidacja MIME + rozszerzenia + rozmiaru, losowe nazwy plików, storage nigdy nie serwowany bezpośrednio z katalogu aplikacji — dostęp publiczny wyłącznie przez CDN lub reverse proxy. Nigdy nie ufaj `Content-Type` z requestu.
- Publiczne API: tylko odczyt w fazie 1; rate limiting (DRF throttling / warstwa reverse proxy przed aplikacją).
- Nagłówki bezpieczeństwa: HSTS, CSP, X-Content-Type-Options, Referrer-Policy. CSP bez `unsafe-inline` dla skryptów.
- Zależności skanowane w CI (`pip-audit`, `npm audit`); aktualizacje przez Dependabot/Renovate.
- Backupy Postgresa automatyczne, z testowanym odtwarzaniem (restore drill, nie tylko backup).
- Sekrety wyłącznie w zmiennych środowiskowych (`.env` poza repo, `env.example` jako szablon bez wartości) — nic w repo, nic w logach, nic w komunikatach błędów zwracanych klientowi.
- Draft nigdy nie wycieka publicznym API — filtruj po `status` w queryset, nie w serializerze ani na froncie.
