---
description: Pełna weryfikacja lokalna — lint, typecheck, testy, Django check. Uruchom przed uznaniem zadania za skończone.
allowed-tools: Bash, Read, Grep, Glob
---

Uruchom pełną weryfikację i zaraportuj wynik.

Stan repo:
!`git status --short`

## Kroki

1. Backend: `ruff check`, `mypy` (lub `pyright`), `python manage.py check`, `pytest`.
2. Frontend: `npm run lint`, `npm run typecheck`, `npm test`.
3. Migracje: `python manage.py makemigrations --dry-run` — jeśli wykryje niezacommitowane zmiany modeli, zgłoś to jako błąd.

## Raport

Podaj tylko: co przeszło, co nie przeszło, i dokładną lokalizację każdego błędu (plik:linia). Bez streszczania logów.
Nie naprawiaj niczego bez pytania — najpierw raport.
