---
paths:
  - "backend/**/*.py"
  - "frontend/**/*.{ts,tsx}"
---

# Konwencje i TDD

- Treści serwisu po polsku. Kod, nazwy (klasy, funkcje, zmienne, pola) i commity po angielsku — komentarze mogą być po polsku, zgodnie z resztą repo. Wyjątek: nazwy pól/metod, które celowo odzwierciedlają treść widoczną dla redaktora w panelu (np. `status_pl`/`status_en` w `blog/admin.py`).
- Python: type hints wszędzie, `ruff` (lint+format), `mypy`/`pyright` na nowym kodzie.
- TypeScript: `strict`, brak `any` bez uzasadnienia w komentarzu.
- Migracje Django: zawsze commitowane i przeglądane, nigdy nie edytuj zaaplikowanej migracji.

## TDD
- Dla logiki nietrywialnej (walidacja, serializery, hooki, endpointy) — test przed lub równolegle z kodem, nie po. Red → green → refactor.
- Backend: `pytest` + `pytest-django`. Frontend: `Vitest` + `Testing Library`.
- Nowy endpoint, model z logiką lub komponent z logiką = wymagany test; brak testu blokuje merge.
- Coverage to sygnał, nie cel — priorytet: ścieżki krytyczne i edge case'y.
- Obowiązkowe przypadki brzegowe dla bloga: pusta lista postów, nieistniejący slug (404), post w statusie `draft` **i** `archived` (oba niewidoczne publicznie), paginacja poza zakresem, brak obrazu okładki, **post bez tłumaczenia EN** (żądanie wersji, która nie istnieje lub nie jest opublikowana), slug z jednego języka użyty w routingu drugiego.

## Commity
- Małe, atomowe, Conventional Commits (`feat:`, `fix:`, `chore:`, `test:`, `refactor:`).
- Migracja Django w osobnym commicie niż zmiana logiki, jeśli obie są duże.
