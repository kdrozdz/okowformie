# 16 — Pliki do pobrania (nowa pozycja menu + panel + publiczne API + frontend)

- **Cel:** Nowa pozycja menu „Do pobrania" — lista plików (na start: PDF) zarządzana w panelu redakcyjnym (dodawanie, sortowanie, zmiana widoczności `draft`/`published`/`archived`, trwałe usunięcie), wystawiona publicznym API i wyrenderowana na froncie. Nowa domenowa aplikacja `downloads`. Storage lokalny (wolumen) teraz, przez abstrakcję Django `STORAGES` — przejście na S3 w przyszłości bez zmian w modelu (otwarta decyzja w `CLAUDE.md`, `scope.md`).
- **Status:** backend + frontend gotowe, review `qa-agent` zamknięte (GO, jedno znalezisko naprawione od razu) — zostało `/check` i `/code-review`.

## Decyzje wejściowe (z brainstormingu)

- Nazwa/opis pliku **tłumaczone PL/EN** (jak `Post`/`AboutMe`), nie wspólne jak `Certificate.name`.
- Sam plik **wspólny** dla obu wersji językowych (jeden upload, nie osobny per język).
- Widoczność: **reużycie wzorca `draft`/`published`/`archived`** (`core.constants.PublicationStatus`), per tłumaczenie — spójne z resztą panelu. Trwałe usunięcie = skasowanie rekordu w adminie.
- Dozwolone typy plików na start: **tylko PDF** (YAGNI, rozszerzalne później).

## Plan

- [x] backend-agent: nowa aplikacja `downloads` (domenowo, wg `scope.md`) — modele `Download` (wspólne: `file`, `order`) + `DownloadTranslation` (per język: `title`, `description`, `status`, `published_at`, `updated_at`), `django-parler`, migracje.
- [x] backend-agent: `downloads/validators.py: validate_pdf_upload` — rozszerzenie `.pdf`, limit rozmiaru, weryfikacja realnej zawartości (magic bytes), nie tylko `Content-Type`/rozszerzenia (`.claude/rules/security.md`). Zostaje lokalnie w `downloads` (pierwsze użycie — próg wydzielenia do `core` to trzecie powtórzenie, `engineering-principles.md`).
- [x] backend-agent: queryset/manager (`published(language_code)`, sortowanie po `order`) — wzorzec `blog.managers`/`PostQuerySet`.
- [x] backend-agent: panel admina `DownloadAdmin` (`TranslatableAdmin`) — kolumny tytuł + status PL/EN (redaktor widzi braki tłumaczeń, `.claude/rules/content-admin.md`), pole `order`, fieldsety (plik osobno od nazwy/opisu, publikacja osobno).
- [x] backend-agent: publiczny endpoint `GET /api/v1/{lang}/downloads/?page=n` (`ListAPIView`, wzorzec `PostListView`) — tylko `published`, paginacja (domyślny `PAGE_SIZE`), throttling (osobny scope `downloads`), `Cache-Control`.
- [x] backend-agent: rejestracja `downloads` w `INSTALLED_APPS`, `backend/urls.py`, throttle rate w `settings.py`.
- [x] frontend-agent: link „Do pobrania" / „Downloads" w `PrimaryNav` + `dictionary.ts`, strona `/[lang]/do-pobrania` (RSC + fetch, ISR jak posty), `getDownloads(lang, page)` w `lib/api/client.ts` + typy w `lib/api/types.ts`.
- [x] qa-agent: niezależne review (regresje, bezpieczeństwo uploadu, testy, zgodność z rules).
- [x] naprawa znalezisk z review qa-agent.
- [ ] `/check` — zielone.
- [ ] `/code-review` (poziom medium) — znaleziska naprawione.

## Poza zakresem tego taska

Kategorie/tagi dla plików (otwarta decyzja, nie dotyczy tej listy), integracja S3 (przyszła faza — dziś tylko abstrakcja `STORAGES` gotowa na zmianę backendu), inne typy plików poza PDF.

## Decyzje po drodze

### Bez sluga i bez pól SEO na `DownloadTranslation`
Plan wymieniał tylko `title`/`description`/`status`/`published_at`/`updated_at` — zgodnie z tym `DownloadTranslation` nie ma sluga ani `meta_title`/`meta_description`, w przeciwieństwie do `PostTranslation`/`AboutMeTranslation`. Uzasadnienie: plik do pobrania nie ma własnej strony szczegółu (tylko wpis na jednej liście, `GET /api/v1/{lang}/downloads/`), więc te pola byłyby martwe — dodanie ich „na wszelki wypadek" łamałoby YAGNI (`.claude/rules/engineering-principles.md`).

### `description` jako `TextField`, nie `CharField`
Plan dopuszczał oba warianty. Wybrany `TextField`, bo Django admin renderuje go domyślnie jako `Textarea` — bez potrzeby dopisywania osobnego `forms.py` tylko po to, żeby podmienić widget (jak `about.forms.AboutMeAdminForm` robi dla `meta_description`). Brak custom formularza w ogóle: `downloads` nie ma logiki „gotowości do publikacji" ani walidacji SEO minimalnej długości — `file`/`title` są wymagane już na poziomie pola modelu, a `description` jest opcjonalne, więc nie było żadnej reguły biznesowej, która uzasadniałaby własny `ModelForm` (KISS).

### Bez kolorowych kropek statusu w adminie
Zadanie explicite wykluczało kopiowanie `blog.admin.PostAdmin._status_badge` (kolorowe kropki HTML) — `DownloadAdmin.status_pl`/`status_en` zwracają zwykły tekst (`get_status_display()` albo `"brak wersji"`). Jedna, prosta lista plików nie uzasadnia tego nakładu.

### Nazwa indeksu `DownloadTranslation` musiała być skrócona
`makemigrations` odrzucił pierwszą próbę (`downloads_downloadtr_public_list`, 32 znaki) z `models.E034`: Django ogranicza nazwy **indeksów** (nie `UniqueConstraint`) do 30 znaków, niezależnie od backendu — historyczny limit MySQL, wymuszany przez Django globalnie. Finalna nazwa: `downloads_dltr_public_list` (26 znaków, `dltr` = skrót "DownloadTranslation", analogicznie do `blog`'s `posttr`). `UniqueConstraint` (`downloads_downloadtranslation_unique_language_per_download`, 58 znaków) nie ma tego ograniczenia — ten sam wzorzec co `about.models.AboutMeTranslation.Meta.constraints` (51 znaków), więc został bez skracania.

### `RandomFilenameUploadTo` użyte wprost, bez legacy powodu `blog`/`about`
`Download.file` używa `core.storage.RandomFilenameUploadTo("downloads/files")` bezpośrednio (jak `branding`), a nie kopii wzorca `post_cover_upload_to`/`about_photo_upload_to` — `downloads` to nowa domena bez istniejących, zaaplikowanych migracji referencujących starą funkcję, więc nie ma powodu, dla którego `blog`/`about` jeszcze nie zostały zretrofitowane (`core/storage.py`, docstring).

### `Download.file` bez wariantu `None` w serializerze
W przeciwieństwie do opcjonalnych obrazów w `blog`/`about` (`cover_image`, `photo`, `certificate.image` — wszystkie `blank=True`), `Download.file` jest wymagane na poziomie modelu (bez `blank=True`) — plik do pobrania bez pliku nie ma sensu. `DownloadListSerializer.get_file` nie ma więc gałęzi `None`, w przeciwieństwie do analogicznych metod w `blog`/`about`.

### Kategoria admina „Treść"
`Download` dopisany do istniejącej kategorii `_APP_LIST_CATEGORIES["content"]` w `backend/admin.py` (obok `blog.post`/`about.aboutme`) — spójne z tym, że to trzecia domena treściowa redagowana przez tę samą, nietechniczną osobę. Wymagało aktualizacji istniejącego testu `test_superuser_widzi_kazdy_model_we_wlasciwej_kategorii` (`backend/tests/test_admin_site.py`) — bez fallbacku „Inne" model i tak by się pojawił (poprawka z `/code-review` na tasku 15), ale jawna kategoria jest lepszym UX.

### Migracja w osobnym commicie
`0001_initial.py` scommitowany osobno od reszty logiki (`.claude/rules/conventions.md`), tak jak `docs/tasks/9-strona-o-mnie.md`.

### `Pagination` generalizowany o `basePath` zamiast literalnego reużycia
Zadanie zakładało reużycie `Pagination` bez zmian, ale komponent budował `href` na sztywno z `/${lang}/posty` — literalne podpięcie go pod `/do-pobrania` linkowałoby paginację listy plików z powrotem do listy postów. Zamieniono prop `lang` (używany wyłącznie do budowy tego linku) na `basePath: string` (np. `/pl/posty`, `/pl/do-pobrania`) — wywołujący (strona) podaje pełną ścieżkę, komponent dokleja tylko `?page=`. Zaktualizowano jedyne dotychczasowe miejsce wywołania (`posty/page.tsx`, ten sam wynikowy `href` co wcześniej — bez zmiany zachowania) i test (`Pagination.test.tsx`, dopisany przypadek z `basePath="/pl/do-pobrania"`, snapshoty bez zmian treściowych poza propsem). Uzasadnienie: `engineering-principles.md` (odwrócenie zależności — komponent nie zna konkretnej domeny), a nie literalna interpretacja „bez zmian”, która złamałaby poprawność.

### `npm test` już istniał
Plan sugerował możliwy brak skryptu `test` w `package.json` — w praktyce już istnieje (`vitest run`, dodany przy wcześniejszym tasku z Vitest+Testing Library), więc nie było potrzeby go dokładać.

### Snapshot `Header.test.tsx.snap` zaktualizowany
Dodanie trzeciego linku nawigacji (`PrimaryNav`) zmieniło markup `Header` — 4 snapshoty w `Header.test.tsx.snap` przeregenerowane (`vitest run -u`) i ręcznie zweryfikowane w diffie: jedyna zmiana to doklejony `<a href="/{lang}/do-pobrania">{Do pobrania|Downloads}</a>`, bez regresji w istniejącym markupie.

## Wynik weryfikacji lokalnej — backend (2026-09-23)

Wszystko uruchomione przez `docker compose exec -T backend uv run ...` (kontenery już działały, `docker compose ps` — patrz notatka niżej o gunicornie i OpenTelemetry).

- `uv run ruff check .` → `All checks passed!`
- `uv run mypy src` → `Success: no issues found in 142 source files`
- `uv run python manage.py makemigrations --check --dry-run` → `No changes detected` (migracja `downloads/migrations/0001_initial.py` już zawiera cały schemat)
- `uv run python manage.py check` → `System check identified no issues (2 silenced)`
- `uv run python manage.py migrate downloads` → `Applying downloads.0001_initial... OK`
- `uv run pytest src/downloads -q` → `32 passed in 1.58s`
- `uv run pytest -q` (cały backend) → `2 failed, 323 passed` — oba faile to `src/core/tests/test_telemetry.py`, **niezwiązane z tym taskiem**: kontener `backend` ma `OTEL_METRICS_ENABLED=True` z `docker-compose.yml:101` (`${OTEL_METRICS_ENABLED:-True}`), a te dwa testy zakładają `False`. Potwierdzone jako środowiskowe, nie regresja: `docker compose exec -T -e OTEL_METRICS_ENABLED=False backend uv run pytest src/core/tests/test_telemetry.py -q` → `13 passed`. Zgłoszone w `docs/todo/TODO.md` (nowy wpis `[otwarte]`, 2026-09-23), nie naprawiane w tym tasku (poza zakresem `downloads`).
- `uv run python manage.py spectacular --file ...` → schema generuje się poprawnie, `/api/v1/{lang}/downloads/` obecny w kontrakcie (`DownloadList`, `PaginatedDownloadListList`); istniejące 4 errory/1 warning (`about`/`branding`) są pre-existing, niezwiązane z `downloads`.

Przy okazji zaktualizowany istniejący test `backend/src/backend/tests/test_admin_site.py::test_superuser_widzi_kazdy_model_we_wlasciwej_kategorii` (rozszerzony o `("downloads", "download")`) — regresja spodziewana po dopisaniu `Download` do kategorii „Treść", nie defekt.

**Nie zrobione w tym przebiegu (poza zakresem backend-agenta):** frontend (`docs/tasks/16-pliki-do-pobrania.md` → sekcja frontend-agent), `qa-agent`, `/code-review`.

## Wynik weryfikacji lokalnej — frontend (2026-09-23)

Nowe/zmienione pliki:
- `frontend/src/lib/api/types.ts` — `Download` interface.
- `frontend/src/lib/api/client.ts` — `getDownloads(lang, page)`.
- `frontend/src/lib/i18n/dictionary.ts` — `header.navDownloads`, sekcja `downloads` (PL/EN).
- `frontend/src/components/Header/PrimaryNav.tsx`, `Header.tsx` — trzeci link menu + snapshot zaktualizowany.
- `frontend/src/components/Pagination/Pagination.tsx` (+ `.test.tsx`) — `basePath` zamiast `lang` (patrz „Decyzje po drodze”).
- `frontend/src/app/[lang]/posty/page.tsx` — dostosowany do nowego propu `Pagination`.
- `frontend/src/components/DownloadList/DownloadList.tsx` (+ `.module.css`, `.test.tsx`) — nowy komponent listy.
- `frontend/src/app/[lang]/do-pobrania/page.tsx` (+ `page.test.ts`) — nowa strona.

Komendy i wynik:
- `npm run lint` → czysto, brak błędów/ostrzeżeń.
- `npm run typecheck` → czysto, brak błędów.
- `npm test` (`vitest run`) → `16 passed (16 test files), 89 passed (89 tests)` — w tym nowe: `DownloadList.test.tsx` (3 testy: pusta lista, render tytułu/opisu/linku pobierania, brak pustego `<p>` dla pustego `description`), `do-pobrania/page.test.ts` (`parsePage`, 9 testów analogicznych do `posty/page.test.ts`), rozszerzony `Pagination.test.tsx` (nowy przypadek `basePath` spoza `/posty`), zaktualizowany snapshot `Header.test.tsx.snap` (3. link nawigacji).

Weryfikacja wizualna: sprawdzone przez `curl` na żywym `docker compose` (`frontend`/`backend` już działały, port 3000/8000) — nie w przeglądarce/MCP, ale przez realny render Next.js dev servera pod adresem, jaki zobaczyłaby przeglądarka:
- `GET /pl/do-pobrania` → `<h1>Do pobrania</h1>`, pusty stan „Brak plików do pobrania.” (baza nie ma jeszcze żadnego opublikowanego pliku — `GET /api/v1/pl/downloads/` zwraca `{"count":0,...,"results":[]}`), canonical/hreflang/OG poprawne.
- `GET /en/do-pobrania` → pusty stan „No downloads available yet.”, `<title>Downloads | okowFormie</title>`.
- `GET /pl/do-pobrania?page=999` → `404` (strona poza zakresem paginacji, zgodnie ze wzorcem `posty`).
- Link „Do pobrania”/„Downloads” obecny w menu na `/pl/do-pobrania`, `/pl/posty`, `/pl/o-mnie` (i analogicznie EN) — na stronie `/pl/do-pobrania` ma `aria-current="page"`.

Nie sprawdzone: realny render z niepustą listą (brak danych testowych w bazie — plan backendu nie zakładał seed danych), stany 375/768/1440px w przeglądarce (brak dostępu do przeglądarki/MCP w tej sesji — CSS `DownloadList.module.css` napisany mobile-first z rozszerzeniem `min-width: 768px` analogicznie do `PostList.module.css`, ale nie zweryfikowany wizualnie na realnych szerokościach).

## Wynik review qa-agent (2026-09-23)

**Werdykt: GO, bez blokerów.** Niezależnie potwierdzone (nie tylko z raportów innych agentów): `ruff check` czysty, `mypy src` czysty, `pytest src/downloads` 32/32, `makemigrations --check` bez zmian, `npm run lint`/`typecheck` czyste, `npm test` 89/89. Sprawdzone bez zastrzeżeń: regresja `Pagination`/`basePath` (brak — identyczny wynikowy `href`), bezpieczeństwo uploadu (magic bytes faktycznie sprawdzane, kolejność sprawdzeń tania→droga), wyciek draftów (filtrowanie w querysecie, nie w serializerze), N+1/paginacja (testy realnie liczą zapytania), zakres faz (czysto), konwencje/typy, panel redakcyjny (`status_pl`/`status_en` pokazują braki tłumaczeń).

**Znalezisko #1 (Medium, a11y) — naprawione od razu.** `DownloadList.tsx` — link pobierania miał identyczny, nierozróżnialny tekst dostępny ("Pobierz plik") na każdej pozycji listy; czytnik ekranu w trybie "lista linków" nie odróżniał, który plik pobiera dany link. Naprawa: `aria-label={\`${downloadLabel}: ${download.title}\`}` na `<a>`. Test `DownloadList.test.tsx` zaktualizowany (asercja po pełnym `aria-label`, nie po samym `downloadLabel`).

**Znalezisko #2 (Low, UX) — naprawione przy okazji.** Pobrany plik dostawał losową nazwę (`RandomFilenameUploadTo` generuje UUID na storage — świadoma, poprawna decyzja bezpieczeństwa, `.claude/rules/security.md`) zamiast czytelnej. Dodano `frontend/src/lib/format/filename.ts::downloadFilename(title, fileUrl)` — slugifikuje tytuł (z jawną mapą polskich znaków specjalnych, bo NFKD nie rozkłada np. „ł"), doklejä rozszerzenie z realnego URL-a pliku. Użyty jako wartość atrybutu `download` w `DownloadList.tsx`. 5 nowych testów (`filename.test.ts`).

**Znalezisko #3 (Low, poza zakresem brancha) — zgłoszone do `docs/todo/TODO.md`, nie naprawiane tu.** Brak twardego limitu rozmiaru requestu (`DATA_UPLOAD_MAX_MEMORY_SIZE`/nginx `client_max_body_size`) przed walidacją uploadu — dotyczy całego backendu (identyczna, pre-existing luka istnieje już dla `blog`/`about`), nie regresja tego taska. Szczegóły: `docs/todo/TODO.md`, wpis „Brak twardego limitu rozmiaru requestu przed walidacją uploadu”.

Po naprawach: `npm run lint`/`typecheck` czyste, `npm test` → **17 plików testowych, 94 testy przeszły** (było 16/89, +1 plik `filename.test.ts` z 5 testami, `DownloadList.test.tsx` zaktualizowany bez zmiany liczby testów).
