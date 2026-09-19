---
description: Review bieżących zmian przez qa-agent — regresje, bezpieczeństwo, testy, zgodność z rules.
argument-hint: [opcjonalnie: branch bazowy, domyślnie main]
allowed-tools: Bash, Read, Grep, Glob, Agent
---

Zmiany do review:
!`git diff --stat $(git merge-base HEAD main 2>/dev/null || echo main)...HEAD`

Deleguj review do `qa-agent`. Przekaż mu pełny diff i wymagaj sprawdzenia:

1. **Regresje** — czy zmiana łamie istniejące zachowanie; czy testy pokrywają nową ścieżkę.
2. **Bezpieczeństwo** — sanityzacja HTML, walidacja uploadu, wyciek draftów przez publiczne API, sekrety w kodzie (`.claude/rules/security.md`).
3. **Wydajność** — N+1, brak indeksu, brak paginacji, niepotrzebny `"use client"` (`.claude/rules/performance.md`).
4. **Zakres faz** — czy nie wjechało nic z fazy 2/3 (`.claude/rules/scope.md`).
5. **Konwencje** — type hints, brak `any`, testy dla nowej logiki (`.claude/rules/conventions.md`).

## Wyjście

Lista ustaleń posortowana od najpoważniejszego, każde z lokalizacją `plik:linia` i konkretnym scenariuszem awarii. Bez ogólników typu "rozważ dodanie testów".
Jeśli nic nie znaleziono — powiedz to wprost, nie wymyślaj uwag na siłę.
