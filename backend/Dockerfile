# syntax=docker/dockerfile:1
#
# Cztery stage'e:
#   base     - wspólny fundament (Python + uv + zależności).
#   dev      - obraz z dev-dependencies (ruff/pytest/mypy), `runserver`,
#              root (bind-mount z hosta + non-root user to klasyczne
#              piekło uprawnień; w dev prostota > izolacja).
#              docker-compose (infra-agent) celuje w ten target i montuje
#              `./backend:/app`, żeby zmiany w kodzie odświeżały się bez
#              rebuildu obrazu.
#   builder  - tylko zależności produkcyjne, do skopiowania do `runtime`.
#   runtime  - obraz produkcyjny: bez uv/kompilatorów/dev-tools, kontener
#              działa jako user `app` (nie root), serwer `gunicorn`.
#
# Domyślny target buildu (bez --target) to `runtime`, żeby `docker build`
# bez flag zawsze dawał bezpieczny obraz produkcyjny.

FROM python:3.14-slim AS base

COPY --from=ghcr.io/astral-sh/uv:0.12.1 /uv /uvx /usr/local/bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH" \
    DJANGO_SETTINGS_MODULE=backend.settings

WORKDIR /app

# Warstwa zależności osobno od kodu, żeby cache Dockera trafiał częściej
# przy samej zmianie kodu.
COPY pyproject.toml uv.lock ./

# --- dev --------------------------------------------------------------

FROM base AS dev

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-install-project

COPY manage.py ./
COPY src ./src

EXPOSE 8000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

# --- builder (tylko zależności produkcyjne) --------------------------------

FROM base AS builder

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-install-project

COPY manage.py ./
COPY src ./src

# --- runtime (produkcja) ----------------------------------------------

FROM python:3.14-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH" \
    DJANGO_SETTINGS_MODULE=backend.settings

WORKDIR /app

# Kontener nie działa jako root.
RUN groupadd --system app && useradd --system --gid app --home-dir /app app

COPY --from=builder --chown=app:app /app/.venv /app/.venv
COPY --from=builder --chown=app:app /app/manage.py /app/manage.py
COPY --from=builder --chown=app:app /app/src /app/src

RUN mkdir -p /app/staticfiles && chown app:app /app/staticfiles

USER app

EXPOSE 8000

# migrate+collectstatic na starcie kontenera: prosty i wystarczający dla
# jednego web-serwisu w fazie 1. Przy wielu replikach naraz (skalowanie
# poziome) `migrate` powinien się przenieść do osobnego kroku deployu
# (release/init container), żeby uniknąć równoległego uruchomienia
# migracji z wielu kontenerów — decyzja dla infra-agenta przy tamtej
# fazie.
CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py collectstatic --noinput && gunicorn backend.wsgi:application --bind 0.0.0.0:8000 --workers 3"]
