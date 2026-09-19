---
description: Zaplanuj i rozbij nową funkcję na kroki między agentami, z kontrolą zakresu faz.
argument-hint: [opis funkcji]
allowed-tools: Read, Grep, Glob, Bash, Agent
---

Funkcja: $ARGUMENTS

## Kroki

1. **Kontrola zakresu** — sprawdź `.claude/rules/scope.md`. Jeśli funkcja należy do fazy 2/3, **zatrzymaj się** i powiedz to wprost zamiast planować implementację.
2. **Rozbicie** — podziel na zadania per agent w kolejności: `uiux-agent` (jeśli dotyczy UI) → `backend-agent` → `frontend-agent` → `qa-agent`. `seo-agent`, jeśli funkcja dotyka treści publicznej.
3. **Kontrakt** — jeśli funkcja zmienia API, najpierw uzgodnij kształt endpointu (OpenAPI), potem implementacja po obu stronach.
4. **Kryteria akceptacji** — wypisz je przed kodem: zachowanie, przypadki brzegowe, budżet wydajności.

## Wyjście

Plan z listą kroków, przypisaniem do agentów i kryteriami akceptacji. **Czekaj na akceptację przed implementacją.**
