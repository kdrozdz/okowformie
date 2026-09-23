# 16 — Pliki do pobrania (nowa pozycja menu + panel + publiczne API + frontend)

- **Cel:** Nowa pozycja menu „Do pobrania" — lista plików (na start: PDF) zarządzana w panelu redakcyjnym (dodawanie, sortowanie, zmiana widoczności `draft`/`published`/`archived`, trwałe usunięcie), wystawiona publicznym API i wyrenderowana na froncie. Nowa domenowa aplikacja `downloads`. Storage lokalny (wolumen) teraz, przez abstrakcję Django `STORAGES` — przejście na S3 w przyszłości bez zmian w modelu (otwarta decyzja w `CLAUDE.md`, `scope.md`).
- **Status:** backend gotowy (modele, panel, publiczne API, testy, `/check` lokalnie zielone) — frontend, `qa-agent` i `/code-review` jeszcze do zrobienia.

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
- [ ] frontend-agent: link „Do pobrania" / „Downloads" w `PrimaryNav` + `dictionary.ts`, strona `/[lang]/do-pobrania` (RSC + fetch, ISR jak posty), `getDownloads(lang, page)` w `lib/api/client.ts` + typy w `lib/api/types.ts`.
- [ ] qa-agent: niezależne review (regresje, bezpieczeństwo uploadu, testy, zgodność z rules).
- [ ] naprawa znalezisk z review qa-agent.
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
