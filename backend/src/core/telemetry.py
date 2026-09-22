"""Metryki OpenTelemetry eksponowane w formacie Prometheusa.

Wołane wyłącznie z `core.apps.CoreConfig.ready()`, i tylko gdy
`OTEL_METRICS_ENABLED=True` (patrz `backend/src/backend/settings.py`) —
guard zapobiega próbie zbindowania portu 9464 przez każdą jednorazową
komendę `manage.py` (migrate, test, shell) w dev.
"""

import logging
import os
import sys
import time
from typing import Any

from django.core.signals import got_request_exception
from django.http import HttpRequest
from opentelemetry import metrics
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.instrumentation.django import DjangoInstrumentor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.view import ExplicitBucketHistogramAggregation, View
from opentelemetry.sdk.resources import Resource
from prometheus_client import start_http_server

logger = logging.getLogger(__name__)

METRICS_PORT = 9464

# Granice bucketów (sekundy) dla `django_db_query_duration_seconds`. Bez tej
# `View` OTel SDK stosuje domyślne granice zaprojektowane pod *milisekundy*
# (`[0, 5, 10, 25, 50, 75, 100, 250, 500, 750, 1000, 2500, 5000, 7500, 10000]`)
# — przy jednostce sekund prawie cały ruch (zapytania SQL bloga trwają
# ułamki ms do pojedynczych ms) ląduje w pierwszym niezerowym buckecie
# (`le=5.0`, czyli 5 *sekund*), co czyni `histogram_quantile` w Grafanie
# bezsensownym (zweryfikowane empirycznie: p95 pokazywał 4.75s przy realnym
# p95 rzędu milisekund — `docs/todo/TODO.md`). Zakres dobrany pod realną
# skalę: od ułamka milisekundy do kilku sekund (margines na wolniejsze
# zapytania), nie pod hipotetyczne obciążenie.
_DB_QUERY_DURATION_BUCKETS_SECONDS = (
    0.0005,
    0.001,
    0.0025,
    0.005,
    0.01,
    0.025,
    0.05,
    0.1,
    0.25,
    0.5,
    1,
    2.5,
    5,
)

# Zainicjalizowane raz w `setup_telemetry()`, wołanej raz na proces
# (`CoreConfig.ready()`) — moduł-poziomu `global` akceptowalny tu, bez
# klasy/singletona na wyrost (YAGNI, `.claude/rules/engineering-principles.md`).
_exception_counter = None
_db_query_duration = None


def setup_telemetry() -> None:
    # `manage.py runserver` z domyślnym autoreloaderem (używanym przez
    # `docker-compose.yml`, target `dev`) uruchamia CAŁY proces `manage.py`
    # dwukrotnie jako dwa osobne procesy OS: raz w procesie-rodzicu (watcher,
    # bez zmiennej `RUN_MAIN`), raz w faktycznym procesie serwującym (dziecko,
    # `RUN_MAIN=true`, odpalone jako subprocess przez `autoreload`). Oba
    # wołają `django.setup()` → `AppConfig.ready()` → tę funkcję. Bez tego
    # guardu oba próbują zbindować `METRICS_PORT` — rodzic wygrywa wyścig,
    # dziecko (jedyny proces faktycznie obsługujący ruch) pada z
    # `OSError: Address already in use` i cały kontener `backend` nie startuje
    # (zweryfikowane empirycznie przy pierwszym `docker compose up`, task 14
    # sekcja 5). Guard uruchamia telemetrię tylko w procesie, który faktycznie
    # będzie serwował ruch: dziecku reloadera (`RUN_MAIN=true`) albo — gdy
    # reloader w ogóle nie jest używany (`--noreload`, gunicorn, `manage.py
    # test`/`shell` z `OTEL_METRICS_ENABLED=True` ręcznie) — w jedynym
    # istniejącym procesie.
    is_runserver_reload_watcher = (
        "runserver" in sys.argv
        and "--noreload" not in sys.argv
        and os.environ.get("RUN_MAIN") != "true"
    )
    if is_runserver_reload_watcher:
        return

    # Wołane synchronicznie z `CoreConfig.ready()`, co Django wymaga żeby się
    # powiodło — bez tego try/except każdy błąd tutaj (port 9464 zajęty z
    # innego powodu niż reloader, przyszła zmiana zależności rzucająca w
    # `DjangoInstrumentor`) wywaliłby cały proces Django, nie tylko metryki.
    # Kod obserwowalności nie może być pojedynczym punktem awarii dla
    # aplikacji, którą ma obserwować — backend startuje bez metryk zamiast
    # się nie uruchomić. Wzorzec logowania jak w
    # `ai_content/services.py::generate_post_content` (`logger.exception`).
    try:
        resource = Resource.create({"service.name": "backend"})
        reader = PrometheusMetricReader()
        db_query_duration_view = View(
            instrument_name="django_db_query_duration_seconds",
            aggregation=ExplicitBucketHistogramAggregation(
                boundaries=_DB_QUERY_DURATION_BUCKETS_SECONDS,
            ),
        )
        provider = MeterProvider(
            resource=resource,
            metric_readers=[reader],
            views=[db_query_duration_view],
        )
        metrics.set_meter_provider(provider)

        meter = metrics.get_meter("backend.core")

        global _exception_counter
        _exception_counter = meter.create_counter(
            "django_unhandled_exceptions_total",
            description="Liczba nieobsłużonych wyjątków w widokach Django, wg typu i ścieżki.",
        )
        got_request_exception.connect(_record_exception)

        global _db_query_duration
        _db_query_duration = meter.create_histogram(
            "django_db_query_duration_seconds",
            description="Czas trwania zapytań SQL, wg operacji (SELECT/INSERT/UPDATE/DELETE/...).",
            unit="s",
        )

        # Serwer HTTP scrape'owany przez Prometheusa — PrometheusMetricReader
        # sam go nie stawia, trzeba jawnie (udokumentowane zachowanie biblioteki).
        start_http_server(port=METRICS_PORT)

        # `DjangoInstrumentor` faktycznie emituje metryki HTTP (zweryfikowane
        # empirycznie, task 14 sekcja 5). `PsycopgInstrumentor`/`RedisInstrumentor`
        # (usunięte tu) integrują się wyłącznie przez `TracerProvider` — nie
        # skonfigurowany w tym tasku (decyzja: metryki, nie traces) — więc były
        # no-opem mimo że `.instrument()` nie rzucało błędu. DB zastąpione
        # własnym licznikiem niżej (`DBQueryMetricsMiddleware`); Redis świadomie
        # poza zakresem (`docs/todo/TODO.md`).
        DjangoInstrumentor().instrument()
    except Exception:
        logger.exception(
            "Nie udało się zainicjalizować telemetrii OpenTelemetry — "
            "backend działa dalej bez metryk."
        )


def _record_exception(sender: object, request: HttpRequest | None = None, **kwargs: object) -> None:
    exc_type = sys.exc_info()[0]
    exc_name = exc_type.__name__ if exc_type else "unknown"
    path = request.path if request is not None else "unknown"
    assert _exception_counter is not None
    _exception_counter.add(1, {"exception_type": exc_name, "path": path})


def _record_db_query(
    execute: Any,
    sql: str,
    params: Any,
    many: bool,
    context: dict[str, Any],
) -> Any:
    """Callback dla `connection.execute_wrapper` — mierzy czas zapytania SQL.

    Zastępuje `PsycopgInstrumentor` (usunięty, patrz `setup_telemetry`), który
    nie produkował żadnych metryk bez `TracerProvider`. `execute_wrapper` to
    udokumentowany hak Django do tego dokładnie celu:
    https://docs.djangoproject.com/en/stable/topics/db/instrumentation/
    """
    start = time.perf_counter()
    try:
        return execute(sql, params, many, context)
    finally:
        duration = time.perf_counter() - start
        operation = sql.split(maxsplit=1)[0].upper() if sql else "UNKNOWN"
        if _db_query_duration is not None:
            _db_query_duration.record(duration, {"operation": operation})


class DBQueryMetricsMiddleware:
    """Mierzy czas zapytań SQL wykonanych w trakcie obsługi requestu.

    No-op (zero narzutu) gdy `OTEL_METRICS_ENABLED=False` — domyślny stan
    poza kontenerem `backend` w `docker-compose.yml`, więc `pytest`/
    `manage.py` nigdy nie wchodzi w `execute_wrapper`.
    """

    def __init__(self, get_response: Any) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> Any:
        from django.conf import settings
        from django.db import connection

        if not settings.OTEL_METRICS_ENABLED:
            return self.get_response(request)
        with connection.execute_wrapper(_record_db_query):
            return self.get_response(request)
