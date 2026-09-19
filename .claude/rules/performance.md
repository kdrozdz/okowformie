---
paths:
  - "frontend/**"
  - "backend/**"
---

# Wydajność

**Budżet:** Core Web Vitals — LCP < 2.5s, CLS < 0.1, INP < 200ms. Lighthouse Performance/SEO ≥ 90 na stronie posta i liście. Budżet jest kryterium akceptacji, nie aspiracją.

## Frontend
- SSG/ISR z rewalidacją po publikacji posta (webhook z backendu lub time-based).
- `next/image`, WebP/AVIF, rozmiary responsywne, lazy loading. Obraz okładki nad zgięciem: `priority`, reszta lazy.
- React Server Components domyślnie; `"use client"` tylko gdy potrzebna interaktywność.
- Code-splitting; nie dokładaj zależności client-side pod jednorazowe użycie.
- Rezerwuj wymiary obrazów i osadzeń, żeby nie generować CLS.

## Backend
- `select_related`/`prefetch_related` zamiast N+1.
- Indeksy na `slug` (unique), `status`, `published_at`; indeks złożony pod listę publiczną (`status`, `-published_at`).
- Paginacja obowiązkowa na listach — brak endpointu zwracającego wszystko.
- Lista postów nie serializuje pełnej treści, tylko excerpt.
- Cache HTTP (`Cache-Control`, ETag) + CDN (CloudFront) przed API i mediami.
