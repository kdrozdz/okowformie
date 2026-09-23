# 16 — Pliki do pobrania (nowa pozycja menu + panel + publiczne API + frontend)

- **Cel:** Nowa pozycja menu „Do pobrania" — lista plików (na start: PDF) zarządzana w panelu redakcyjnym (dodawanie, sortowanie, zmiana widoczności `draft`/`published`/`archived`, trwałe usunięcie), wystawiona publicznym API i wyrenderowana na froncie. Nowa domenowa aplikacja `downloads`. Storage lokalny (wolumen) teraz, przez abstrakcję Django `STORAGES` — przejście na S3 w przyszłości bez zmian w modelu (otwarta decyzja w `CLAUDE.md`, `scope.md`).
- **Status:** w toku

## Decyzje wejściowe (z brainstormingu)

- Nazwa/opis pliku **tłumaczone PL/EN** (jak `Post`/`AboutMe`), nie wspólne jak `Certificate.name`.
- Sam plik **wspólny** dla obu wersji językowych (jeden upload, nie osobny per język).
- Widoczność: **reużycie wzorca `draft`/`published`/`archived`** (`core.constants.PublicationStatus`), per tłumaczenie — spójne z resztą panelu. Trwałe usunięcie = skasowanie rekordu w adminie.
- Dozwolone typy plików na start: **tylko PDF** (YAGNI, rozszerzalne później).

## Plan

- [ ] backend-agent: nowa aplikacja `downloads` (domenowo, wg `scope.md`) — modele `Download` (wspólne: `file`, `order`) + `DownloadTranslation` (per język: `title`, `description`, `status`, `published_at`, `updated_at`), `django-parler`, migracje.
- [ ] backend-agent: `downloads/validators.py: validate_pdf_upload` — rozszerzenie `.pdf`, limit rozmiaru, weryfikacja realnej zawartości (magic bytes), nie tylko `Content-Type`/rozszerzenia (`.claude/rules/security.md`). Zostaje lokalnie w `downloads` (pierwsze użycie — próg wydzielenia do `core` to trzecie powtórzenie, `engineering-principles.md`).
- [ ] backend-agent: queryset/manager (`published(language_code)`, sortowanie po `order`) — wzorzec `blog.managers`/`PostQuerySet`.
- [ ] backend-agent: panel admina `DownloadAdmin` (`TranslatableAdmin`) — kolumny tytuł + status PL/EN (redaktor widzi braki tłumaczeń, `.claude/rules/content-admin.md`), pole `order`, fieldsety (plik osobno od nazwy/opisu, publikacja osobno).
- [ ] backend-agent: publiczny endpoint `GET /api/v1/{lang}/downloads/?page=n` (`ListAPIView`, wzorzec `PostListView`) — tylko `published`, paginacja (domyślny `PAGE_SIZE`), throttling (osobny scope `downloads`), `Cache-Control`.
- [ ] backend-agent: rejestracja `downloads` w `INSTALLED_APPS`, `backend/urls.py`, throttle rate w `settings.py`.
- [ ] frontend-agent: link „Do pobrania" / „Downloads" w `PrimaryNav` + `dictionary.ts`, strona `/[lang]/do-pobrania` (RSC + fetch, ISR jak posty), `getDownloads(lang, page)` w `lib/api/client.ts` + typy w `lib/api/types.ts`.
- [ ] qa-agent: niezależne review (regresje, bezpieczeństwo uploadu, testy, zgodność z rules).
- [ ] naprawa znalezisk z review qa-agent.
- [ ] `/check` — zielone.
- [ ] `/code-review` (poziom medium) — znaleziska naprawione.

## Poza zakresem tego taska

Kategorie/tagi dla plików (otwarta decyzja, nie dotyczy tej listy), integracja S3 (przyszła faza — dziś tylko abstrakcja `STORAGES` gotowa na zmianę backendu), inne typy plików poza PDF.

## Decyzje po drodze

(uzupełniane w trakcie implementacji)
