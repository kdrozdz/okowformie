# Żywy frontend Next.js (O mnie + Posty)

- **Cel:** przekształcić zaakceptowany mockup (`frontend/mockups/szkielet-frontendu.html`) w realną strukturę Next.js — realna nawigacja (nie JS-owe zakładki), dane pobierane z istniejącego publicznego API (`/api/v1/{lang}/about/`, `/api/v1/{lang}/posts/`), z fejkowymi danymi seed w bazie, żeby było co renderować.
- **Status:** w toku

## Kontekst / decyzje wejściowe

- Model `Certificate` (FK→`AboutMe`) **już istnieje** w `backend/src/about` wraz z publicznym API — nie jest to nowa funkcja, tylko konsumpcja istniejącego kontraktu.
- Frontend to nietknięty szkielet `create-next-app` — brak realnych stron/komponentów, brak TanStack Query w `package.json` (mimo decyzji w `docs/decisions/2026-09-19-tanstack-query.md`).
- Brak fixtures/management commands w repo — to pierwsza taka konwencja.
- `seo-agent` uczestniczy **od etapu projektowania routingu/metadanych** (doradza przed implementacją), nie tylko jako końcowy audyt — na wyraźną prośbę.

## Plan

- [x] `backend-agent`: komenda `seed_demo_data` (poziom projektu `backend/src/backend/management/commands/`) — staff user, singleton `AboutMe` PL/EN, 8 `Certificate`, 3+ `Post` PL (min. 1 z tłumaczeniem EN), obrazy generowane programistycznie (Pillow, bez commitowania binarek), idempotentna. Dodatkowo: `"backend"` w `INSTALLED_APPS` (inaczej Django nie widzi komendy) i serwowanie `MEDIA_URL` w `DEBUG` (inaczej URL-e obrazów z API są martwe lokalnie). Zweryfikowane: `ruff`, `mypy`, `pytest` (169 passed) zielone, `curl` na żywym API potwierdza dane.
- [x] `seo-agent` (doradczo): struktura tras `/[lang]/o-mnie`, `/[lang]/posty(/[slug])`, `generateMetadata` z pól API (`meta_title`/`meta_description`), hreflang PL↔EN + x-default, canonical. Znalazł 2 blokery P0 (mockup nieobecny na tym branchu, brak server-only `API_URL`) — oba naprawione przed implementacją.
- [x] `frontend-agent`: routing `/[lang]/...` zamiast zakładek JS, Server Components + `fetch()` do API (bez TanStack Query), `next.config.ts` → `images.remotePatterns`, komponenty 1:1 z mockupu (Header, Footer, AboutSection, CertificatesSlider — client, PostList/PostCard, PostDetail), CSS Modules. Zweryfikowane: `lint`/`typecheck`/realny `next build` zielone, pełna macierz endpointów przez curl, hreflang/canonical/JSON-LD obecne i poprawne. Znaleziony i naprawiany osobno: `og:image`/`twitter:image` wskazywały na wewnętrzny host kontenera (`backend:8000`) zamiast publicznego adresu — błąd backendu (`build_absolute_uri` z `Host` requestu), nie frontendu.
- [ ] `seo-agent`: audyt końcowy nowych tras (metadata/hreflang/canonical) — sitemap.xml/robots.txt poza zakresem tego taska (dotyczą całej witryny)
- [ ] `qa-agent`: setup Vitest + React Testing Library (pierwszy komponent z logiką — `CertificatesSlider`), lekki test `seed_demo_data`, review całości pod kątem regresji/bezpieczeństwa
- [ ] `/code-review` — druga, niezależna para oczu przed mergem (workflow z `CLAUDE.md`: „review (qa-agent + /code-review) zamknięte")
- [ ] `/check` zielone, merge do `dev`

## Decyzje po drodze

- Komenda `seed_demo_data` wymagała dodania `"backend"` (pakiet projektu) do `INSTALLED_APPS` — bez tego `manage.py` nie widzi `management/commands/` na poziomie projektu.
- Media w dev serwowane bezpośrednio przez Django (`static()` w `urls.py`) tylko pod `DEBUG=True` — na produkcji nadal przez reverse proxy/CDN, zgodnie z `security.md`.
