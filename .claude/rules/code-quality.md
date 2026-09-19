---
paths:
  - "backend/**/*.py"
  - "frontend/**/*.{ts,tsx}"
---

# Jakość kodu przy pisaniu

Kryteria review obowiązują **w trakcie pisania**, nie dopiero przy `/review`. Chodzi o to, żeby `qa-agent` nie znajdował rzeczy, które dało się nie popełnić.

## Zanim dopiszesz nowy kod
- Sprawdź, czy coś podobnego już istnieje (`Grep`/`Glob`) — nowa funkcja robiąca to, co istniejąca, to defekt, nie feature.
- Rozszerz istniejące rozwiązanie, zamiast tworzyć drugie obok. Abstrakcja dopiero przy trzecim powtórzeniu (`engineering-principles.md`).

## Poziom abstrakcji
- Pisz na poziomie problemu, nie o dwa poziomy niżej „na wszelki wypadek". Warstwa konfiguracji, hook czy klasa bazowa pod jedno użycie to przerost.
- Nazwy mówią co robi, nie jak jest zaimplementowane.

## Ścieżki błędu są częścią zadania
- Happy path to połowa roboty. Każda funkcja sięgająca po sieć, bazę, plik albo dane użytkownika ma zdefiniowane zachowanie przy braku danych, błędzie i wartości pustej.
- Nie połykaj wyjątków bez logu i bez decyzji, co dalej.

## Samo-review przed oddaniem
Przejdź świadomie po wymiarach z `.claude/commands/review.md` (regresje, bezpieczeństwo, wydajność, zakres faz, konwencje) — ich treść jest w regułach, które i tak masz w kontekście. Nie przepisuj ich tutaj, po prostu sprawdź.

## Dowód zamiast deklaracji
- „Działa" liczy się dopiero po uruchomieniu. Podaj realne wyjście komend z sekcji Komendy w `CLAUDE.md`.
- Jeśli coś nie przechodzi albo nie dało się sprawdzić — napisz to wprost. Zgłoszony problem jest tańszy niż znaleziony na produkcji.
