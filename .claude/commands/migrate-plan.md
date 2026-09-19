---
description: Zaplanuj zmianę modelu Django przed jej wykonaniem — pokaż SQL, wykryj operacje destrukcyjne.
argument-hint: [opis zmiany modelu]
allowed-tools: Bash, Read, Grep, Glob
---

Zaplanuj zmianę: $ARGUMENTS

Aktualny stan migracji:
!`cd backend && python manage.py showmigrations 2>&1 | tail -20`

## Kroki

1. Znajdź dotknięte modele i opisz zmianę w kategoriach schematu (dodanie/usunięcie/zmiana typu kolumny, indeks, constraint).
2. `python manage.py makemigrations --dry-run --verbosity 3` — pokaż, co Django wygeneruje.
3. Dla każdej operacji oceń ryzyko:
   - **Destrukcyjna** (DROP COLUMN, zmiana typu, usunięcie modelu) — wymaga jawnej zgody i planu migracji danych.
   - **Blokująca** (dodanie NOT NULL bez default na dużej tabeli, tworzenie indeksu bez CONCURRENTLY) — zaproponuj wariant bezpieczny.
   - **Bezpieczna** — dodanie nullable, nowy model, nowy indeks CONCURRENTLY.
4. Sprawdź, czy zmiana nie łamie kontraktu `/api/v1/`. Jeśli łamie — zaproponuj wersjonowanie zamiast breaking change.

## Wyjście

Plan z listą operacji, oceną ryzyka i rekomendacją. **Nie uruchamiaj `makemigrations` ani `migrate`** — czekaj na akceptację.
