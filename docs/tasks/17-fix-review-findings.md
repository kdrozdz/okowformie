# Naprawa znalezisk z `/code-review high`

- **Cel:** naprawić realne bugi/regresje znalezione podczas przeglądu całego dotychczasowego stanu projektu (`/code-review high` na `origin/main...HEAD`).
- **Status:** w toku

## Plan
- [x] `blog/admin.py::PostAdmin` — duplikacja wierszy w liście (JOIN na `translations` bez `.distinct()`), ten sam bug co naprawiony wcześniej w `downloads.admin.DownloadAdmin`. Dodano `.distinct()` w `get_queryset()`, usunięto `ordering="translations__title"` z `admin_title` (Postgres wymaga kolumny `ORDER BY` w `SELECT DISTINCT`), regresyjny test w `blog/tests/test_admin.py`.
- [x] `DownloadButton.tsx` — fallback na błąd fetch cofa się do `window.open()` (zachowanie sprzed fixa `860320b`), ale **celowe i pokryte testem** (`DownloadButton.test.tsx`: "nie zostawia martwego przycisku"), więc nie cofnięto go — dodano tylko widoczny, tłumaczony komunikat błędu (`role="alert"`, klucz `downloads.downloadError` w `dictionary.ts` PL/EN), żeby fallback nie był cichy. `DownloadButton`/`DownloadList` dostały nowe wymagane propsy `errorMessage`/`errorClassName`/`downloadErrorMessage`, testy zaktualizowane, `npm run lint`/`typecheck`/`test` (100/100) zielone.
- [ ] Pozostałe znaleziska z reviewu (obserwowalność, duplikacja throttle, naruszenie `scope.md` w `ai_content`, drobne wydajnościowe) — nie są bugami, tylko dług/ulepszenia; do osobnej decyzji, czy wchodzą w zakres tego taska.

## Decyzje po drodze
- Branch `17-fix-review-findings` odbity z `main` (repo nie ma brancha `dev`, patrz pamięć projektu).
- Pełny raport reviewu (10 znaleziska, ranking wg wagi) — w transkrypcie sesji, nie duplikowany tutaj.
