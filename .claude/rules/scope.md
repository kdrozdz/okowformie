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
- Media w S3 od początku (bez migracji plików przy fazie 2).
- Sekrety wyłącznie w env / AWS Secrets Manager.
- DNS: rekordy cyberfolks → AWS; planuj subdomeny pod przyszłe fazy (`app.`, `kursy.`).
