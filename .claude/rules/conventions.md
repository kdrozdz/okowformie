---
paths:
  - "backend/**/*.py"
  - "frontend/**/*.{ts,tsx}"
---

# Konwencje i TDD

- Treści serwisu po polsku; kod, nazwy, komentarze, commity po angielsku.
- Python: type hints wszędzie, `ruff` (lint+format), `mypy`/`pyright` na nowym kodzie.
- TypeScript: `strict`, brak `any` bez uzasadnienia w komentarzu.
- Migracje Django: zawsze commitowane i przeglądane, nigdy nie edytuj zaaplikowanej migracji.

## TDD
- Dla logiki nietrywialnej (walidacja, serializery, hooki, endpointy) — test przed lub równolegle z kodem, nie po. Red → green → refactor.
- Backend: `pytest` + `pytest-django`. Frontend: `Vitest` + `Testing Library`.
- Nowy endpoint, model z logiką lub komponent z logiką = wymagany test; brak testu blokuje merge.
- Coverage to sygnał, nie cel — priorytet: ścieżki krytyczne i edge case'y.
- Obowiązkowe przypadki brzegowe dla bloga: pusta lista postów, nieistniejący slug (404), post w statusie draft (niewidoczny publicznie), paginacja poza zakresem, brak obrazu okładki.

## Commity
- Małe, atomowe, Conventional Commits (`feat:`, `fix:`, `chore:`, `test:`, `refactor:`).
- Migracja Django w osobnym commicie niż zmiana logiki, jeśli obie są duże.
