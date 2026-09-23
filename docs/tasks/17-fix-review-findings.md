# Naprawa znalezisk z `/code-review high`

- **Cel:** naprawić realne bugi/regresje znalezione podczas przeglądu całego dotychczasowego stanu projektu (`/code-review high` na `origin/main...HEAD`).
- **Status:** gotowe

## Plan
- [x] `blog/admin.py::PostAdmin` — duplikacja wierszy w liście (JOIN na `translations` bez `.distinct()`), ten sam bug co naprawiony wcześniej w `downloads.admin.DownloadAdmin`. Dodano `.distinct()` w `get_queryset()`, usunięto `ordering="translations__title"` z `admin_title` (Postgres wymaga kolumny `ORDER BY` w `SELECT DISTINCT`), regresyjny test w `blog/tests/test_admin.py`.
- [x] `DownloadButton.tsx` — fallback na błąd fetch cofa się do `window.open()` (zachowanie sprzed fixa `860320b`), ale **celowe i pokryte testem** (`DownloadButton.test.tsx`: "nie zostawia martwego przycisku"), więc nie cofnięto go — dodano tylko widoczny, tłumaczony komunikat błędu (`role="alert"`, klucz `downloads.downloadError` w `dictionary.ts` PL/EN), żeby fallback nie był cichy. `DownloadButton`/`DownloadList` dostały nowe wymagane propsy `errorMessage`/`errorClassName`/`downloadErrorMessage`, testy zaktualizowane, `npm run lint`/`typecheck`/`test` (100/100) zielone.
- [x] Pozostałe znaleziska z reviewu (obserwowalność, duplikacja throttle, naruszenie `scope.md` w `ai_content`, drobne wydajnościowe) — nie są bugami, tylko dług/ulepszenia. Zdecydowano: poza zakresem tego taska ("napraw bugi najpierw"), zapisane jako osobne wpisy `[otwarte]` w `docs/todo/TODO.md`, żeby nie zniknęły z kontekstu (`.claude/rules/todo.md`). Jeden z 10 (kolizja portu metryk przy gunicornie multi-worker) już miał istniejący wpis w TODO — nie duplikowany.

## Decyzje po drodze
- Branch `17-fix-review-findings` odbity z `main` (repo nie ma brancha `dev`, patrz pamięć projektu).
- Pełny raport reviewu (10 znaleziska, ranking wg wagi) — w transkrypcie sesji, nie duplikowany tutaj.
- Cykl review (`.claude/rules/code-quality.md`/pamięć projektu) złapał dwa kolejne, prawdziwe regresje CSS w poprawce `DownloadButton`, obie naprawione od razu:
  - `qa-agent`: `<a>` + `<p role="alert">` jako Fragment stawały się dwoma osobnymi flex-itemami `.card` → na desktopie `justify-content: space-between` rozjeżdżał przycisk i komunikat. Fix: wspólny kontener (`wrapperClassName`).
  - `/code-review medium`: nowy kontener zgubił `align-self: flex-start`, więc na mobile rozciągał się na całą szerokość karty. Fix: przywrócone na `.downloadWrapper`.
  - `/code-review low` po obu poprawkach: czysto.
- Backend: `uv run pytest` (329/329), `ruff check`, `mypy src` — zielone. Frontend: `npm run lint`, `npm run typecheck`, `npm test` (100/100) — zielone.
- Wizualna weryfikacja w przeglądarce **nie została wykonana** — user odmówił instalacji rozszerzenia Claude in Chrome, wbudowana przeglądarka niedostępna w tej sesji. Poprawki CSS zweryfikowane statycznie (box model, dwa niezależne review) i pokryte dwoma kolejnymi rundami reviewu, ale realny render na 375/768px nie był obejrzany.
