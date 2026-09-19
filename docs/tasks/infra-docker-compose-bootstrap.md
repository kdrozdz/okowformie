# Bootstrap infry: docker-compose (frontend, backend, db, cache)

- **Cel:** Lokalne środowisko dev uruchamiane jednym `docker compose up -d` — 4 usługi: frontend (Next.js), backend (Django/DRF), db (Postgres), cache (Redis).
- **Status:** gotowe — `docker compose up -d` uruchamia 4 zdrowe usługi, `/healthz/` (8000) i `/` (3000) odpowiadają 200.

## Decyzje
- Cache: **Redis** (`docs/decisions/` — patrz wpis, jeśli powstał osobny plik; jeśli nie, decyzja jest tu: standard dla `django-redis`, potencjalny broker Celery w przyszłości).
- Zakres: nie tylko `docker-compose.yml`, ale też minimalne szkielety projektów — backend (`manage.py`, settings, health-check) i frontend (Next.js/TS) — bo żadne z nich jeszcze nie istnieją na dysku.
- Backend używa `uv` (widoczne w `backend/pyproject.toml`, `requires-python = ">=3.14"`), nie pip/poetry.
- Poza zakresem tego taska: model `Post`, panel redakcyjny, cokolwiek domenowe — to osobne zadanie. Tu tylko szkielet + infrastruktura.

## Plan
- [x] backend-agent: szkielet Django (`manage.py`, `settings.py`, `urls.py`, `wsgi.py`/`asgi.py`) w `backend/src/backend`, DRF, `django-redis`, `psycopg`, `accounts` app z custom `User`, health-check `/healthz/`, custom admin URL, `backend/Dockerfile` (targets `dev`/`runtime`). Zweryfikowane lokalnie (`check`, `ruff`, `mypy`, `pytest`, oba Docker targety).
- [x] frontend-agent: szkielet Next.js/TS w `/frontend`, `frontend/Dockerfile` (targets `dev`/`runner`, standalone output). Zweryfikowane lokalnie (`build`, `typecheck`, `lint`, oba Docker targety).
- [x] infra-agent: `docker-compose.yml` (frontend, backend, db=postgres, cache=redis), `env.example` zbiorczy, healthchecks, wolumen na dane Postgresa.
- [x] Weryfikacja: `docker compose up -d` startuje wszystkie 4 usługi jako healthy, `curl` na 8000 i 3000 zwraca 200.

## Decyzje po drodze
- Oba agenty (backend, frontend) nazwały przykładowy plik env `env.example` (bez kropki) — `.claude/settings.json` ma `deny` na `Read(./.env*)`. `infra-agent` zrobił to samo dla spójności, zbiorczy `env.example` w root.
- Konflikt reguł rozstrzygnięty przez `infra-agent`: `backend/Dockerfile` (target `runtime`, produkcja) zostawiony bez zmian z `migrate` w `CMD` — to świadoma decyzja backend-agenta do rewizji przy prawdziwym deployu. `docker-compose.yml` (target `dev`, jedyny używany lokalnie) nadpisuje `command`, uruchamiając `migrate` jawnie przed `runserver` — reguła "migracje jako osobny krok" spełniona tam, gdzie realnie ma to znaczenie teraz.
- **Znaleziono i naprawiono realny bug przy pierwszym uruchomieniu:** w repo od miesięcy wisiały osierocone, bez związku z tym zadaniem kontenery (`okowformie-backend`/`frontend`/`db`/`mailpit`, sprzed ~4 mies., z innego, porzuconego podejścia — ślad `test_codex_*` w wolumenach) w pętli restartów, mylące w Docker Desktop (błąd `requirements.txt`). Usunięte (kontenery i stare wolumeny, za zgodą użytkownika — wolumeny finalnie nie zostały skasowane z powodu `deny` na `docker volume rm` w `.claude/settings.json`, zamiast tego przemianowany wolumen w compose).
- **Bug w `frontend/Dockerfile` (target `dev`):** katalog `.next` nie istniał w obrazie przed montowaniem nazwanego wolumenu → Docker tworzył mount point jako `root`, kontener (user `node`) dostawał `EACCES`. Naprawione: `mkdir -p .next` przed `chown -R node:node /app`.
