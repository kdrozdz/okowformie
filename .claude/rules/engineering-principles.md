# Zasady inżynierskie

Ten plik nie ma `paths:` — obowiązuje w każdej decyzji projektowej.

Działaj jak Senior/Staff Engineer. Krótka referencja:

- **YAGNI** — nie buduj pod hipotetyczne wymagania. Wyjątek: zasady przyszłościowe z `scope.md`, które są świadomą, uzasadnioną decyzją.
- **KISS / DRY** — najprostsze rozwiązanie, które działa; abstrakcja dopiero przy trzecim powtórzeniu, nie przy drugim.
- **Boy Scout Rule** — zostaw kod czystszym, ale w zakresie zadania; nie refaktoruj przy okazji całych modułów.
- **Zasada najmniejszego zaskoczenia** — nazwy i zachowania zgodne z konwencjami Django/Next, nie autorskie.
- **Odwracalność** — preferuj decyzje odwracalne. Nieodwracalne (schemat bazy, kontrakt publicznego API, wybór hostingu lub usługi zewnętrznej) wymagają planu i akceptacji przed implementacją.
- **Hyrum's Law** — publiczne API to zobowiązanie; po publikacji zmieniaj przez wersjonowanie, nie przez breaking change.
- **Piramida testów** — dużo unit, mniej integration, minimum e2e.
- **Pojedyncza odpowiedzialność** — jedna klasa/funkcja, jeden powód do zmiany. W Django objawia się to konkretnie: logika biznesowa poza widokami i serializerami, model nie wie o HTTP, widok nie zna szczegółów zapisu.
- **Odwrócenie zależności** — kod zależy od abstrakcji, nie od konkretnego dostawcy. Praktycznie: media przez `STORAGES` Django, nie przez ścieżki lokalne ani klienta S3 wpisanego na sztywno (storage to wciąż otwarta decyzja — patrz `CLAUDE.md`). To samo dotyczy cache'a i dostawcy modelu AI.
- **Diagnoza przed naprawą** — zanim zaczniesz naprawiać, sprawdź, co *faktycznie* działa, a nie co powinno działać. Objaw pasujący do znanej awarii często ma inną przyczynę; restart, przebudowa czy zmiana konfiguracji bez potwierdzonej diagnozy to zgadywanie.

## Kiedy się zatrzymać i zapytać

Tylko poniższe przypadki wymagają zgody, zanim implementacja pojedzie dalej:

- Zmiana schematu bazy wymagająca migracji danych.
- Zmiana kontraktu API (`/api/v1/`) po jego publikacji.
- Nowa usługa zewnętrzna (hosting, storage, dostawca modelu AI) lub nowa zależność w stacku.
- Cokolwiek z fazy 2/3.
- Sprzeczność między zadaniem a którąkolwiek z reguł w `.claude/rules/`.

## Poza tą listą: działaj z automatu

Gdy plan/kontrakt API zostały raz uzgodnione i żaden z powyższych warunków nie zachodzi, dalszy ciąg — delegacja do subagentów, implementacja, uruchamianie `/check`, `/code-review`, naprawa znalezisk z reviewu — leci jednym ciągiem, **bez** zatrzymywania się po każdym kroku po osobne potwierdzenie. Pytanie o zgodę na każdy kolejny, rutynowy krok (kolejny agent, kolejna komenda weryfikacyjna, poprawka znaleziska z reviewu) jest samo w sobie tarciem, którego ta lista ma unikać — jeśli krok nie pasuje do żadnego punktu wyżej, wykonaj go i zgłoś wynik, zamiast pytać przed wykonaniem.
