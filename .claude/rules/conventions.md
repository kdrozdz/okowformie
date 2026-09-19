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

## Fetchowanie danych (frontend)
- Domyślnie: RSC + fetch po stronie serwera, SSG/ISR (`performance.md`). `"use client"` + `useQuery` (TanStack Query) tylko gdy dane zależą od interakcji klienta (wyszukiwarka, filtry, paginacja bez przeładowania) — nie jako domyślny sposób pobierania danych. Uzasadnienie i alternatywy: `docs/decisions/2026-09-19-tanstack-query.md`.
- Jeden `QueryClientProvider` w korzeniu drzewa klienckiego. Query keys spójne z endpointami `/api/v1/`.
- Globalny state manager (Redux/Zustand) poza zakresem fazy 1 — brak stanu rozproszonego do zarządzania (koszyk/konto to faza 2, `scope.md`). Nie dokładaj na zapas.

## Responsywność
- Mobile-first: style bazowe pod mobile, rozszerzenia w górę przez `min-width` media queries (Tailwind: klasa bez prefiksu = mobile, `sm:`/`md:`/`lg:` dokładają się na większe ekrany) — nie odwrotnie (`max-width` jako wyjątek, nie domyślny wzorzec).
- Breakpointy i zachowanie per widok specyfikuje `uiux-agent` (375/768/1440) — frontend-agent implementuje zgodnie z tą specyfikacją, nie ustala breakpointów samodzielnie.

## TDD
- Dla logiki nietrywialnej (walidacja, serializery, hooki, endpointy) — test przed lub równolegle z kodem, nie po. Red → green → refactor.
- Backend: `pytest` + `pytest-django`. Frontend: `Vitest` + `Testing Library` (React Testing Library — odpowiednik Testing Library dla komponentów Next.js/React).
- Snapshoty komponentów: `toMatchSnapshot` z Vitest (natywne, bez Jest jako drugiego test runnera) — commituj snapshot razem ze zmianą, review traktuje diff snapshotu jak zmianę kodu, nie jak formalność do zaakceptowania bez czytania.
- Nowy endpoint, model z logiką lub komponent z logiką = wymagany test; brak testu blokuje merge.
- Coverage to sygnał, nie cel — priorytet: ścieżki krytyczne i edge case'y.
- Obowiązkowe przypadki brzegowe dla bloga: pusta lista postów, nieistniejący slug (404), post w statusie `draft` **i** `archived` (oba niewidoczne publicznie), paginacja poza zakresem, brak obrazu okładki, **post bez tłumaczenia EN** (żądanie wersji, która nie istnieje lub nie jest opublikowana), slug z jednego języka użyty w routingu drugiego.

## Commity
- Małe, atomowe, Conventional Commits (`feat:`, `fix:`, `chore:`, `test:`, `refactor:`).
- Migracja Django w osobnym commicie niż zmiana logiki, jeśli obie są duże.
