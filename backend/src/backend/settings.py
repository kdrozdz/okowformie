"""
Konfiguracja Django dla projektu `backend`.

Wszystko, co środowiskowe (sekrety, hosty, baza, cache, CORS), przychodzi
przez zmienne środowiskowe — patrz `/backend/env.example`. Nic z tego nie
jest hardkodowane, zgodnie z `.claude/rules/security.md`.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# `backend/` — katalog z manage.py, dwa poziomy nad tym plikiem
# (src/backend/settings.py -> src/backend -> src -> backend).
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# W dev/lokalnie pozwala trzymać zmienne w `backend/.env`. W kontenerze
# (docker-compose/produkcja) zmienne przychodzą wprost ze środowiska i ten
# plik zwykle nie istnieje — `load_dotenv` wtedy no-opuje.
load_dotenv(BASE_DIR / ".env")


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_list(name: str, default: str = "") -> list[str]:
    raw = os.environ.get(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


# --- Podstawy -----------------------------------------------------------

DEBUG = _env_bool("DEBUG", False)

SECRET_KEY = os.environ.get("SECRET_KEY")
if not SECRET_KEY:
    if DEBUG:
        # Tylko dla dev — nigdy nie używane, gdy DEBUG=False.
        SECRET_KEY = "django-insecure-dev-only-do-not-use-in-production"
    else:
        raise RuntimeError("SECRET_KEY environment variable is required when DEBUG=False")

# Bez wildcardów — jawna lista z env. W dev domyślnie localhost.
ALLOWED_HOSTS = _env_list("ALLOWED_HOSTS", "localhost,127.0.0.1" if DEBUG else "")

CSRF_TRUSTED_ORIGINS = _env_list("CSRF_TRUSTED_ORIGINS")

# --- Aplikacje ------------------------------------------------------------

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "drf_spectacular",
    "corsheaders",
    # Tłumaczenia treści (master + translation) — patrz
    # `docs/decisions/2026-09-19-model-post.md`.
    "parler",
    # Edytor WYSIWYG w panelu redakcyjnym (assety serwowane lokalnie przez
    # staticfiles, bez zewnętrznego CDN — patrz .claude/rules/security.md).
    "django_prose_editor",
    # Apps domenowe (patrz .claude/rules/scope.md — podział domenowy od
    # początku, docelowo obok `accounts` pojawią się `blog`, `shop`, ...).
    "accounts",
    "blog",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "backend.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        # Wymagane przez django.contrib.admin.
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "backend.wsgi.application"
ASGI_APPLICATION = "backend.asgi.application"

# --- Baza danych ------------------------------------------------------------
# `DATABASE_URL` ma pierwszeństwo; alternatywnie osobne POSTGRES_*.

DATABASE_URL = os.environ.get("DATABASE_URL")
if DATABASE_URL:
    import dj_database_url

    DATABASES = {"default": dj_database_url.parse(DATABASE_URL, conn_max_age=600)}
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ.get("POSTGRES_DB", "backend"),
            "USER": os.environ.get("POSTGRES_USER", "backend"),
            "PASSWORD": os.environ.get("POSTGRES_PASSWORD", ""),
            "HOST": os.environ.get("POSTGRES_HOST", "localhost"),
            "PORT": os.environ.get("POSTGRES_PORT", "5432"),
            "CONN_MAX_AGE": 600,
        }
    }

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# --- Cache (Redis) ----------------------------------------------------------

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_URL,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
    }
}

# --- CORS ---------------------------------------------------------------
# Jawna lista originów z env, bez wildcardów (patrz .claude/rules/security.md).

CORS_ALLOWED_ORIGINS = _env_list("CORS_ALLOWED_ORIGINS")

# --- Internacjonalizacja ---------------------------------------------------

LANGUAGE_CODE = "pl"
TIME_ZONE = "Europe/Warsaw"
USE_I18N = True
USE_TZ = True

# Języki treści serwisu. To jedyne źródło prawdy: `parler` bierze stąd
# `choices` dla `PostTranslation.language_code`, a `blog.constants.Language`
# jest z tym zestawiane systemowym checkiem (`blog.checks`), żeby rozjazd
# wyszedł przy `manage.py check`, a nie w produkcji.
LANGUAGES = [
    ("pl", "polski"),
    ("en", "angielski"),
]

# `django-parler`: PL jest językiem domyślnym, EN nie ma fallbacku na PL —
# brak tłumaczenia EN ma być widoczny jako brak (404 / ukrycie na liście),
# a nie po cichu podmieniony polską treścią (`.claude/rules/seo.md`:
# duplikat treści pod innym `hreflang` to problem, nie udogodnienie).
PARLER_DEFAULT_LANGUAGE_CODE = "pl"
PARLER_LANGUAGES = {
    None: (
        {"code": "pl"},
        {"code": "en"},
    ),
    "default": {
        "fallbacks": [],
        "hide_untranslated": True,
    },
}

# --- Pliki statyczne i media ---------------------------------------------

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# Backend storage pozostaje domyślny (`STORAGES`) — wybór docelowego
# magazynu mediów (S3 vs wolumen na VPS) jest otwartą decyzją w `CLAUDE.md`.
# Kod aplikacji nie zakłada ścieżek lokalnych: `upload_to` generuje wyłącznie
# ścieżkę względną, więc podmiana backendu nie wymaga migracji danych
# (`.claude/rules/scope.md`).
MEDIA_URL = os.environ.get("MEDIA_URL", "media/")
MEDIA_ROOT = os.environ.get("MEDIA_ROOT") or BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# `django_prose_editor.W004` przypomina o włączeniu `sanitize=True` na polu
# edytora. Świadomie nie włączamy: sanityzacja HTML-a jest w
# `blog.sanitization`, jedną allowlistą stosowaną przy zapisie **i** przy
# odczycie (`.claude/rules/security.md`). Drugi, wyprowadzany z konfiguracji
# edytora filtr dawałby dwie różne prawdy o tym, co wolno w treści.
SILENCED_SYSTEM_CHECKS = ["django_prose_editor.W004"]

# --- Panel admina pod niestandardowym URL-em -------------------------------
# .claude/rules/security.md: "Panel admina pod niestandardowym URL-em".
# Nadpisywalne przez env (np. inna wartość per środowisko).

ADMIN_URL = os.environ.get("ADMIN_URL", "panel-redakcyjny/")

# --- Django REST Framework -------------------------------------------------
# Bez konfiguracji endpointów domenowych na tym etapie — tylko instalacja.

REST_FRAMEWORK = {
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
}

# --- Twarde ustawienia bezpieczeństwa poza DEBUG ---------------------------

if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = "DENY"
    SECURE_REFERRER_POLICY = "same-origin"
