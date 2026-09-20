.DEFAULT_GOAL := help

.PHONY: help up down restart logs logs-backend logs-frontend ps \
	migrate makemigrations seed superuser backend-shell dbshell \
	lint-backend typecheck-backend test-backend \
	lint-frontend typecheck-frontend test-frontend \
	check

help: ## Pokaż dostępne komendy
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# --- Stack (docker compose) -----------------------------------------------

up: ## Odpal cały stack (frontend, backend, db, cache) w tle
	docker compose up -d

down: ## Zatrzymaj i usuń kontenery stacku
	docker compose down

restart: ## Zrestartuj wszystkie kontenery
	docker compose restart

ps: ## Status kontenerów
	docker compose ps

logs: ## Logi całego stacku (na żywo)
	docker compose logs -f

logs-backend: ## Logi samego backendu (na żywo)
	docker compose logs -f backend

logs-frontend: ## Logi samego frontendu (na żywo)
	docker compose logs -f frontend

# --- Backend (Django) -------------------------------------------------------

migrate: ## Zastosuj migracje Django
	docker compose exec backend uv run manage.py migrate

makemigrations: ## Wygeneruj nowe migracje z bieżących zmian modeli
	docker compose exec backend uv run manage.py makemigrations

seed: ## Wypełnij bazę danymi demo (seed_demo_data) — idempotentne
	docker compose exec backend uv run manage.py seed_demo_data

superuser: ## Utwórz konto admina panelu redakcyjnego
	docker compose exec backend uv run manage.py createsuperuser

backend-shell: ## Interaktywny Django shell
	docker compose exec backend uv run manage.py shell

dbshell: ## Interaktywny psql do bazy projektu
	docker compose exec db psql -U $${POSTGRES_USER:-backend} -d $${POSTGRES_DB:-backend}

lint-backend: ## ruff check na backendzie
	docker compose exec backend uv run ruff check .

typecheck-backend: ## mypy na backendzie
	docker compose exec backend uv run mypy src

test-backend: ## pytest na backendzie
	docker compose exec backend uv run pytest

# --- Frontend (Next.js) ------------------------------------------------------

lint-frontend: ## eslint na frontendzie
	docker compose exec frontend npm run lint

typecheck-frontend: ## tsc --noEmit na frontendzie
	docker compose exec frontend npm run typecheck

test-frontend: ## Vitest na frontendzie
	docker compose exec frontend npm run test

# --- Pełna weryfikacja -------------------------------------------------------

check: lint-backend typecheck-backend test-backend lint-frontend typecheck-frontend test-frontend ## Pełna weryfikacja obu stron (odpowiednik /check) — przerywa na pierwszym błędzie
