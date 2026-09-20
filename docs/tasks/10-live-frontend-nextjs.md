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
- [x] `seo-agent`: audyt końcowy nowych tras (metadata/hreflang/canonical). Znalazł 1 bloker (canonical paginacji kanonizował wszystkie strony do strony 1 — sprzeczne z aktualną wytyczną Google) — naprawiony (self-referencing canonical per stronę, hreflang tylko na stronie 1). Reszta (JSON-LD, 404, hierarchia H1-H6, sanityzacja, fallbacki meta) potwierdzona jako poprawna. sitemap.xml/robots.txt poza zakresem tego taska.
- [x] Live-testowanie przez użytkownika (przeglądarka) ujawniło 4 dodatkowe usterki — wszystkie zdiagnozowane i naprawione bezpośrednio (bez subagenta, drobne/dobrze zlokalizowane): błąd hydratacji (`formatDate` bez jawnej strefy czasowej + potwierdzony fałszywy alarm od rozszerzenia przeglądarki `cz-shortcut-listen`, wyciszony `suppressHydrationWarning` na `<body>`), `next/image` 400/500 (własna regresja przy wcześniejszym "sprzątaniu" `next.config.ts` + brakujący host-rewrite dla fetchu wewnątrz kontenera — `lib/media/image-src.ts`), zbyt długie okno rewalidacji (60s → 15s, zweryfikowane bezpośrednim testem zmiany w bazie), `.gitignore` łapiący też `frontend/src/lib/media/` (zawężone do `/backend/media/`). Zobacz commity `6cb1fcd`, `6eb6fc5`, `89e6059`.
- [x] Makefile z najczęstszymi komendami dev (stack, backend, frontend, `make check`) — testowany (`help`, `ps`, `dbshell`, `lint-backend`, `seed`).
- [ ] `qa-agent`: setup Vitest + React Testing Library (pierwszy komponent z logiką — `CertificatesSlider`), lekki test `seed_demo_data`, review całości pod kątem regresji/bezpieczeństwa. **Pierwsza próba padła na limit sesji w trakcie review, bez zmian w drzewie roboczym — do powtórzenia od zera**, teraz z większym diffem (uwzględniającym fixy z live-testowania).
- [ ] `/code-review` — druga, niezależna para oczu przed mergem (workflow z `CLAUDE.md`: „review (qa-agent + /code-review) zamknięte")
- [ ] `/check` zielone, merge do `dev`

## Decyzje po drodze

- Komenda `seed_demo_data` wymagała dodania `"backend"` (pakiet projektu) do `INSTALLED_APPS` — bez tego `manage.py` nie widzi `management/commands/` na poziomie projektu.
- Media w dev serwowane bezpośrednio przez Django (`static()` w `urls.py`) tylko pod `DEBUG=True` — na produkcji nadal przez reverse proxy/CDN, zgodnie z `security.md`.
- Naprawiony realny bug (nie tylko dev): `request.build_absolute_uri()` w serializerach `about`/`blog` budował URL-e obrazów z `Host` żądania — server-side fetch z kontenera frontendu dawał nieosiągalny `http://backend:8000/...` w `og:image`/JSON-LD. Fix: `SITE_URL` (setting) + `core.api.absolute_media_url()` (wspólny helper). Zweryfikowane na żywo.
- Ten sam publiczny `SITE_URL` w URL-ach obrazów, który naprawia `og:image`, okazał się nieosiągalny dla `next/image` optymalizującego obrazy *wewnątrz* kontenera frontendu — stąd osobny, jednokierunkowy rewrite tylko dla `<Image src>` (`lib/media/image-src.ts`), nigdy dla metadanych.
- Rewalidacja skrócona 60s → 15s po zgłoszeniu „zmiany widoczne dopiero po restarcie" — mechanizm faktycznie działał (zweryfikowane bezpośrednim testem), ale 60s było zbyt długim, mylącym opóźnieniem przy aktywnej edycji treści.
