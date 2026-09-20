# To-do

Rzeczy zauważone po drodze (podczas review, debugowania, `/code-review`),
które nie wchodzą w zakres taska, przy którym zostały znalezione — żeby nie
zniknęły razem z kontekstem rozmowy. To nie jest plan taska (`docs/tasks/`)
ani decyzja architektoniczna (`docs/decisions/`) — surowa lista tego, co
warto kiedyś zrobić.

Jeden plik: `TODO.md`. Każdy wpis w formacie:

```markdown
## [status] Krótki tytuł (YYYY-MM-DD)
Opis problemu w 1-3 zdaniach — na tyle konkretnie, żeby dało się to podjąć
bez odtwarzania śledztwa od zera.

**Kontekst:** link/ścieżka do miejsca, gdzie to zauważono (plik:linia,
plan taska, commit).
```

Statusy: `[otwarte]` / `[w toku]` / `[zrobione]` (+ link do commita/PR).
Wpisów się nie usuwa po zamknięciu — zostają jako historia, tak jak w
`docs/decisions/` i `docs/tasks/`.

Kiedy wpis dojrzeje do realnej pracy — zamień go w plik `docs/tasks/`
(format w tamtejszym `README.md`) i oznacz tu jako `[w toku]` z linkiem do
tego pliku.
