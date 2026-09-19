# Fazy i zakres

Ten plik nie ma `paths:` — ładuje się w każdej sesji. Dyscyplina faz musi być zawsze w kontekście.

1. **Blog** (aktywna) — zakres w `CLAUDE.md`.
2. **Sklep** — konta użytkowników, sprzedaż kursów, rezerwacja wizyt.
3. **Szkolenia online** — dedykowana platforma (narzędzie do wyboru później).

**Nie implementuj nic z faz 2/3, dopóki nie zostanie to jawnie zlecone.** Jeśli zadanie wymaga czegoś z fazy 2/3 — zatrzymaj się i zapytaj, zamiast dobudowywać.

## Zasady przyszłościowe

Przygotowują grunt pod fazy 2/3 bez ich budowania. Ich późniejsza zmiana jest kosztowna:

- Własny model użytkownika od pierwszej migracji (`AUTH_USER_MODEL` = custom `User(AbstractUser)`), nawet pusty w fazie 1.
- Konta redakcyjne (staff) i przyszłe konta klientów to ten sam model `User`, rozróżniany rolami — nie zakładaj, że każdy user to admin.
- Backend API-first, kontrakt wersjonowany (`/api/v1/`); frontend nie zna szczegółów bazy.
- Aplikacje Django podzielone domenowo (`blog`, docelowo `shop`, `bookings`, `accounts`) — nie mieszaj logiki bloga z resztą.
- Media przez abstrakcję storage Django (`STORAGES`) od początku — konkretny backend (S3 vs wolumen na VPS) jest otwartą decyzją w `CLAUDE.md`, ale kod nie może zakładać ścieżek lokalnych na sztywno, żeby zmiana backendu nie wymagała migracji plików.
- Sekrety wyłącznie w zmiennych środowiskowych (`.env` poza repo) — bez AWS Secrets Manager, hosting to Cyberfolks VPS.
- DNS w całości po stronie Cyberfolks; planuj subdomeny pod przyszłe fazy (`app.`, `kursy.`) i pod drugi język, jeśli EN kiedyś dostanie własną subdomenę zamiast prefiksu ścieżki.
- Treść dwujęzyczna PL/EN od pierwszej migracji — model `Post` rozbity na część wspólną i tłumaczenia (`docs/decisions/2026-09-19-model-post.md`). Nie dokładaj pól językowych na płasko (`title_pl`, `title_en`).
