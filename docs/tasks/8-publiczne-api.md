# 8 — Publiczne API bloga (/api/v1/)

- **Cel:** API read-only dla bloga — lista postów (paginacja 5/stronę) i szczegół po slugu, dla PL i EN.
- **Status:** zaimplementowane i przetestowane (`backend-agent`) — implementowane **równolegle** z naprawą defektu #1 na `7-dodanie-postu` (patrz tamten plik), w tym samym working tree, rozłączne pliki (nie dotknięte: `blog/admin.py`, `blog/forms.py`, `blog/tests/test_admin.py`). Branch git jeszcze nie wydzielony — decyzja o rozdzieleniu commitów zapadnie po zakończeniu obu prac.

## Kontrakt (zatwierdzony)

**Lista:** `GET /api/v1/{lang}/posts/?page={n}` — `lang`: `pl`/`en`, inne → 404. `page_size=5`. Odpowiedź: standardowa paginacja DRF. Pola per post: `slug`, `title`, `excerpt`, `cover_image`, `cover_image_alt`, `author`, `published_at` — **bez pełnej treści**.

**Szczegół:** `GET /api/v1/{lang}/posts/{slug}/` — jak wyżej plus `content` (zawsze `content_html`, nigdy surowe pole), `meta_title`, `meta_description`, `updated_at`, `available_translations` (lista `{language, slug}`, **tylko opublikowane**). Brak posta / zły status → 404.

**Dodatkowo:** throttling anonimowych (punkt startowy 60/min), `Cache-Control` na obu endpointach, `drf-spectacular` (schema + docs), autor jako sama nazwa wyświetlana (żadnych danych konta).

## Kryteria akceptacji
- [x] Pusta lista → `200`, `results: []`.
- [x] Nieistniejący slug → `404`.
- [x] `draft`/`archived` niewidoczne (liście i szczególe).
- [x] Post bez tłumaczenia EN → `/api/v1/en/posts/{slug}/` → `404`, nie polska treść.
- [x] Slug istniejący tylko w jednym języku użyty w drugim → `404`.
- [x] Payload `<script>`/`onerror=` w treści → w odpowiedzi wersja po sanityzacji.
- [x] Brak okładki → `cover_image: null`.
- [x] Przekroczony rate limit → `429`.
- [x] Zły `lang` → `404`.
- [x] Brak N+1 — serializery korzystają z istniejącego `PostQuerySet.published()`, nie piszą własnych zapytań.

Testy: `backend/src/blog/tests/test_api_posts.py` (23 przypadki, w tym N+1
mierzony `CaptureQueriesContext` i realne wyczerpanie limitu 60/min do 429).

## Poza zakresem
Frontend (osobny branch po tym), autoryzacja/zapis (fazy 2/3), CDN (dostawca nieustalony — nagłówek `Cache-Control` wystarczy teraz).

## Decyzje po drodze

- **Serializacja tłumaczeń — ręczny serializer, nie `django-parler-rest`.** Kontrakt ma inne nazwy/kształt pól niż domyślny, płaski format parlera (`content` zawsze jako `content_html`, autor jako sama nazwa) — i tak trzeba by nadpisać większość generowanych pól, więc prostszy jest jawny `serializers.Serializer` czytający z już przetestowanej, wolnej od N+1 metody `Post.translations_by_language()` (`blog/managers.py`).
- **Walidacja `lang` na poziomie widoku (`Http404`), nie custom URL converter.** Prostszy kod, spójny JSON `{"detail": ...}` z DRF-owego handlera wyjątków zamiast HTML-owej strony 404 z resolvera Django, gdyby niedopasowanie URL-a zostało załatwione samym wzorcem ścieżki.
- **Autor bez pełnego imienia i nazwiska → fallback `"Redakcja"`, nie `username`.** Kontrakt wprost zakazuje `username` w odpowiedzi (dane konta); `get_full_name()` bywa pusty dla kont testowych/tymczasowych, więc neutralny fallback jest bezpieczniejszy niż cichy powrót do loginu.
- **Throttling: osobny scope `posts` (`AnonRateThrottle` ze `scope = "posts"`), nie domyślny `anon`.** Pozwala stroić limit publicznego API bloga niezależnie od przyszłych publicznych endpointów faz 2/3 bez współdzielenia budżetu żądań. Rate skonfigurowalny przez `BLOG_API_THROTTLE_RATE` (domyślnie `60/min`), zgodnie z zasadą „konfiguracja środowiskowa, nie hardkod" (`.claude/rules/security.md`).
- **`Cache-Control: public, max-age=60` tylko na odpowiedziach `200`.** Błędy (404/429) nie są cache'owane. Wartość `max-age` to punkt startowy do rewizji, gdy zapadnie decyzja o CDN (`CLAUDE.md` → „Otwarte decyzje” → usługi AWS).
- **Routing:** `backend/src/blog/urls.py` (bez własnego prefiksu wersji) dołączony z `backend/src/backend/urls.py` pod `/api/v1/`, zgodnie z zasadą przyszłościową „kontrakt wersjonowany `/api/v1/`" (`.claude/rules/scope.md`). Schema (`/api/v1/schema/`) i docs (`/api/v1/docs/`, Swagger UI) zarejestrowane w `backend/urls.py`, nie w `blog/urls.py` — obejmują całe API, nie tylko domenę bloga.
- **Rozstrzygnięte (2026-09-19): API zwraca `seo_title`/`seo_description`, nie surowe pola.** Redaktor zostawia `meta_title`/`meta_description` puste na co dzień (`content-admin.md`), a `seo.md` zabrania pustego taga w HTML. Zwracanie surowych pól przenosiłoby obowiązek fallbacku na frontend — zdublowana logika w dwóch miejscach, ryzyko rozjazdu (istotne też pod przyszłe posty generowane przez AI, `docs/decisions/2026-09-19-langchain-osobny-task.md`, które przejdą przez te same pola). Fallback jest teraz w jednym miejscu: `PostTranslation.seo_title`/`seo_description` w modelu. Test: `test_api_posts.py::test_puste_pola_seo_maja_fallback_na_tytul_i_zajawke`. Wciąż otwarte: limity długości (60/150–160 znaków) fallback nie wymusza — to nadal tylko podpowiedź w panelu redakcyjnym.
