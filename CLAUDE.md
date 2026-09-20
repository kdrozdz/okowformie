# CLAUDE.md

## Projekt

**okowFormie** — blog optometryczny (soczewki kontaktowe, okulary, zdrowie wzroku, kursy optyczne/ optometrystyczne, wizyty, porad).
Blog (**faza 1, aktywna**) → Sklep + konta + rezerwacje (faza 2) → Szkolenia online (faza 3).
Domena i hosting: Cyberfolks (VPS, linia vroot — patrz `docs/decisions/2026-09-19-hosting-cyberfolks-vps.md`). Autor treści jest osobą nietechniczną — dodaje posty sam, bez developera.

Fazy i zasady przyszłościowe: `.claude/rules/scope.md`. **Nie implementuj nic z faz 2/3 bez jawnego zlecenia.**

## Stack

Next.js/TS · Django+DRF · PostgreSQL · Redis · Docker · Cyberfolks (VPS)

Blog dwujęzyczny **PL/EN od startu** — patrz `docs/decisions/2026-09-19-model-post.md`.

## Zakres fazy 1

W zakresie: model `Post` (+ tłumaczenia PL/EN), panel redakcyjny (`draft` → `published` → `archived`), publiczne API read-only, strony bloga + SEO/GEO, upload obrazów (storage do ustalenia — patrz Otwarte decyzje), deploy + CI.
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
- `/docs/todo/` — znaleziska poza zakresem bieżącego taska (luki, dług techniczny), żeby nie zniknęły z kontekstu czatu. Format i zasada zapisu: `docs/todo/README.md` i `.claude/rules/todo.md`.

## Workflow Git

Każdy task dostaje własny branch, odbity z `dev` — nazwa zgodna z plikiem planu w `/docs/tasks/` (np. `9-strona-o-mnie` dla `docs/tasks/9-strona-o-mnie.md`). Cała praca nad taskiem (kod, migracje, testy, aktualizacje planu) dzieje się na tym branchu, **nigdy bezpośrednio na `dev`**. Merge do `dev` dopiero po zakończeniu — checklista w pliku taska odhaczona, `/check` zielone, review (`qa-agent` + `/code-review`) zamknięte.

## Komendy

```bash
docker compose up -d                                   # cały stack: frontend, backend, db, cache
cd backend && uv run manage.py migrate                 # backend używa uv, nie gołego python
cd backend && uv run manage.py createsuperuser
cd backend && uv run pytest
cd backend && uv run ruff check . && uv run mypy src
cd frontend && npm run dev
cd frontend && npm run lint && npm run typecheck
```

Frontend nie ma jeszcze skryptu `test` (brak Vitest) — do dołożenia przy pierwszym komponencie z logiką, zgodnie z `.claude/rules/conventions.md`.

## Subagenci

Główny agent orkiestruje: deleguje wg katalogu zmiany, integruje wynik.
Zmiana przekrojowa → `uiux-agent` (jeśli UI) → `backend-agent` → `frontend-agent` → `qa-agent`.
`uiux-agent` i `seo-agent` **doradzają** (nie mają `Write`/`Edit`), `frontend-agent` **wdraża**. `qa-agent` nie recenzuje własnego kodu.

| Agent | Zakres |
|---|---|
| `frontend-agent` | `/frontend` |
| `backend-agent` | `/backend` |
| `infra-agent` | `/infra`, `docker-compose.yml`, `.github/` |
| `seo-agent` | audyt SEO + GEO (widoczność w AI) — wdraża Frontend |
| `qa-agent` | testy i review — edytuje tylko katalogi testów |
| `uiux-agent` | specyfikacje UI/UX — wdraża Frontend |

## Slash commands

`/check` pełna weryfikacja · `/migrate-plan` plan zmiany schematu · `/review` review przez QA · `/seo-audit` audyt SEO · `/feature` rozbicie funkcji na kroki

## Konfiguracja Claude Code

- `.claude/rules/` — `scope.md`, `engineering-principles.md` i `todo.md` ładują się zawsze; pozostałe mają `paths:` i wchodzą do kontekstu dopiero przy pracy nad pasującymi plikami.
- `code-quality.md` przenosi kryteria review na etap pisania kodu — `/review` przez `qa-agent` zostaje jako druga para oczu, nie jako pierwsze miejsce, gdzie wychodzą błędy.
- `.claude/agents/` — subagenci. `.claude/commands/` — slash commands. `.claude/settings.json` — uprawnienia (allow/ask/deny).
- Nie duplikuj treści reguł w innych plikach — odsyłaj do nich ścieżką.

## Otwarte decyzje

Nie zgaduj — zapytaj, zanim zaimplementujesz cokolwiek, co od nich zależy:

- **Media/upload obrazów**: S3 jako czysty object storage vs wolumen na VPS Cyberfolks (decyzja o hostingu w `docs/decisions/2026-09-19-hosting-cyberfolks-vps.md` zostawia to pytanie otwarte).
- **Sekrety bez AWS**: `.env` poza repo vs inne narzędzie (Vault itp.) — do ustalenia przy przepisywaniu `infra-agent` pod deploy VPS.
- **Integracja z Instagramem**: czy w fazie 1.
- **Kategorie/tagi**: czy w fazie 1, czy dopiero gdy przybędzie postów.
- **Narzędzie do szkoleń online** (faza 3).

## Rozstrzygnięte (nie otwieraj od nowa)

- **Edytor treści**: WYSIWYG w Django Admin — `docs/decisions/2026-09-19-model-post.md`.
- **Wielojęzyczność**: PL/EN od startu, wzorzec master + tłumaczenia — tamże.
- **Hosting**: Cyberfolks VPS zamiast AWS — `docs/decisions/2026-09-19-hosting-cyberfolks-vps.md`.
- **Generowanie treści przez AI (LangChain)**: osobny task, poza `7-dodanie-postu` — `docs/decisions/2026-09-19-langchain-osobny-task.md`.
