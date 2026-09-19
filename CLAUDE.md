# CLAUDE.md

## Projekt

Blog (**faza 1, aktywna**) → Sklep + konta + rezerwacje (faza 2) → Szkolenia online (faza 3).
Domena i hosting: Cyberfolks (VPS, linia vroot — patrz `docs/decisions/2026-09-19-hosting-cyberfolks-vps.md`). Autor treści jest osobą nietechniczną — dodaje posty sam, bez developera.

Fazy i zasady przyszłościowe: `.claude/rules/scope.md`. **Nie implementuj nic z faz 2/3 bez jawnego zlecenia.**

## Stack

Next.js/TS · Django+DRF · PostgreSQL · S3 · Docker · AWS

## Zakres fazy 1

W zakresie: model `Post`, panel redakcyjny (draft→publish), publiczne API read-only, strony bloga + SEO, upload obrazów do S3, deploy + CI.
Poza zakresem: sklep, płatności, logowanie publiczne, rezerwacje, komentarze, newsletter.

## Struktura repo

```
/backend      Django (DRF, admin)
/frontend     Next.js
/infra        IaC / deployment
/docs         decyzje projektowe i plany tasków w toku
docker-compose.yml
```

Monorepo, backend i frontend wdrażane niezależnie.

## Decyzje i plany tasków

- `/docs/decisions/` — jeden plik na decyzję architektoniczną/projektową, format w `docs/decisions/README.md`. Sprawdź tu przed zmianą czegoś, co mogło już zostać rozstrzygnięte.
- `/docs/tasks/` — plan bieżącego taska, aktualizowany na bieżąco, żeby wznowić pracę po resecie sesji bez odtwarzania kontekstu. Format w `docs/tasks/README.md`.

## Komendy

```bash
docker compose up -d
cd backend && python manage.py migrate
cd backend && python manage.py createsuperuser
cd backend && pytest
cd frontend && npm run dev
cd frontend && npm run lint && npm run typecheck && npm test
```

## Subagenci

Główny agent orkiestruje: deleguje wg katalogu zmiany, integruje wynik.
Zmiana przekrojowa → `uiux-agent` (jeśli UI) → `backend-agent` → `frontend-agent` → `qa-agent`.
`uiux-agent` i `seo-agent` **doradzają** (nie mają `Write`/`Edit`), `frontend-agent` **wdraża**. `qa-agent` nie recenzuje własnego kodu.

| Agent | Zakres |
|---|---|
| `frontend-agent` | `/frontend` |
| `backend-agent` | `/backend` |
| `infra-agent` | `/infra`, `docker-compose.yml`, `.github/` |
| `seo-agent` | audyt SEO — wdraża Frontend |
| `qa-agent` | testy i review — edytuje tylko katalogi testów |
| `uiux-agent` | specyfikacje UI/UX — wdraża Frontend |

## Slash commands

`/check` pełna weryfikacja · `/migrate-plan` plan zmiany schematu · `/review` review przez QA · `/seo-audit` audyt SEO · `/feature` rozbicie funkcji na kroki

## Konfiguracja Claude Code

- `.claude/rules/` — `scope.md` i `engineering-principles.md` ładują się zawsze; pozostałe mają `paths:` i wchodzą do kontekstu dopiero przy pracy nad pasującymi plikami.
- `.claude/agents/` — subagenci. `.claude/commands/` — slash commands. `.claude/settings.json` — uprawnienia (allow/ask/deny).
- Nie duplikuj treści reguł w innych plikach — odsyłaj do nich ścieżką.

## Otwarte decyzje

Nie zgaduj — zapytaj, zanim zaimplementujesz cokolwiek, co od nich zależy:

- **Edytor treści w adminie**: WYSIWYG (TipTap/CKEditor) vs Markdown vs Wagtail zamiast Django Admin.
- **Media/upload obrazów**: S3 jako czysty object storage vs wolumen na VPS Cyberfolks (decyzja o hostingu w `docs/decisions/2026-09-19-hosting-cyberfolks-vps.md` zostawia to pytanie otwarte).
- **Sekrety bez AWS**: `.env` poza repo vs inne narzędzie (Vault itp.) — do ustalenia przy przepisywaniu `infra-agent` pod deploy VPS.
- **Wielojęzyczność**: tylko PL czy PL/EN (wpływa na model `Post` i routing — decyzja przed pierwszą migracją).
- **Integracja z Instagramem**: czy w fazie 1.
- **Kategorie/tagi**: czy w fazie 1, czy dopiero gdy przybędzie postów.
- **Narzędzie do szkoleń online** (faza 3).
