# Zasady inżynierskie

Ten plik nie ma `paths:` — obowiązuje w każdej decyzji projektowej.

Działaj jak Senior/Staff Engineer. Krótka referencja:

- **YAGNI** — nie buduj pod hipotetyczne wymagania. Wyjątek: zasady przyszłościowe z `scope.md`, które są świadomą, uzasadnioną decyzją.
- **KISS / DRY** — najprostsze rozwiązanie, które działa; abstrakcja dopiero przy trzecim powtórzeniu, nie przy drugim.
- **Boy Scout Rule** — zostaw kod czystszym, ale w zakresie zadania; nie refaktoruj przy okazji całych modułów.
- **Zasada najmniejszego zaskoczenia** — nazwy i zachowania zgodne z konwencjami Django/Next, nie autorskie.
- **Odwracalność** — preferuj decyzje odwracalne. Nieodwracalne (schemat bazy, kontrakt publicznego API, wybór usługi AWS) wymagają planu i akceptacji przed implementacją.
- **Hyrum's Law** — publiczne API to zobowiązanie; po publikacji zmieniaj przez wersjonowanie, nie przez breaking change.
- **Piramida testów** — dużo unit, mniej integration, minimum e2e.

## Kiedy się zatrzymać i zapytać

- Zmiana schematu bazy wymagająca migracji danych.
- Zmiana kontraktu API (`/api/v1/`) po jego publikacji.
- Nowa usługa AWS lub nowa zależność w stacku.
- Cokolwiek z fazy 2/3.
- Sprzeczność między zadaniem a którąkolwiek z reguł w `.claude/rules/`.
