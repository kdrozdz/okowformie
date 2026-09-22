"""Telemetria OpenTelemetry → Prometheus (task 14, `.claude/rules/scope.md`
zasada przyszłościowa — kod w `core`, neutralny domenowo).

`setup_telemetry()` binduje realny port TCP (`prometheus_client.start_http_server`)
i rejestruje globalny `MeterProvider` (jednorazowy, cały proces) — oba efekty
uboczne są tu zamockowane/kontrolowane, żeby testy nigdy nie próbowały
faktycznie zbindować portu 9464 (kolizja z `runserver`/innym testem, patrz
guard `is_runserver_reload_watcher` w `core/telemetry.py` i sekcja "Blocker #1"
w `docs/tasks/14-observability-otel-prometheus.md`).

`PsycopgInstrumentor`/`RedisInstrumentor` świadomie nie są tu testowane —
usunięte z `telemetry.py` (okazały się no-opem bez `TracerProvider`, patrz
`docs/decisions/2026-09-22-observability-otel-prometheus.md`), zastąpione
przez `DBQueryMetricsMiddleware`/`_record_db_query`, pokryte niżej.
"""

import sys
import time
from unittest.mock import MagicMock

import pytest
from django.apps import apps as django_apps
from django.http import HttpRequest
from django.test import override_settings
from opentelemetry.instrumentation.django import DjangoInstrumentor
from opentelemetry.sdk.metrics import MeterProvider

from core import telemetry
from core.telemetry import DBQueryMetricsMiddleware, _record_db_query, _record_exception


def test_setup_telemetry_rejestruje_meter_provider_i_instrumentuje_django(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Bypass guardu (argv bez `runserver`) + mock `start_http_server`/
    `DjangoInstrumentor.instrument` — potwierdza, że `setup_telemetry()`
    faktycznie rejestruje `MeterProvider` (nie zostaje na domyślnym no-op
    proxy) i woła instrumentację Django dokładnie raz, bez realnego
    bindowania portu.

    `metrics.set_meter_provider()` i `got_request_exception.connect()` są tu
    też zamockowane — oba to globalny, cały-proces stan współdzielony przez
    cały przebieg `pytest` (`set_meter_provider()` efektywnie działa tylko
    raz na proces, `monkeypatch` nie cofa efektów ubocznych wewnątrz
    wywoływanej funkcji). Bez tego ten test trwale rejestrowałby prawdziwy
    `MeterProvider` i podpinał `_record_exception` pod sygnał na resztę
    suite'u, niezależnie od kolejności uruchamiania plików testowych."""
    monkeypatch.setattr(sys, "argv", ["manage.py", "test"])
    monkeypatch.delenv("RUN_MAIN", raising=False)
    start_http_server_mock = MagicMock()
    monkeypatch.setattr(telemetry, "start_http_server", start_http_server_mock)
    instrument_mock = MagicMock()
    monkeypatch.setattr(DjangoInstrumentor, "instrument", instrument_mock)
    set_meter_provider_mock = MagicMock()
    monkeypatch.setattr(telemetry.metrics, "set_meter_provider", set_meter_provider_mock)
    monkeypatch.setattr(telemetry, "got_request_exception", MagicMock())

    telemetry.setup_telemetry()

    start_http_server_mock.assert_called_once_with(port=telemetry.METRICS_PORT)
    instrument_mock.assert_called_once()
    # Dowód rejestracji bez mutowania realnego globalnego stanu OTel: argument
    # przekazany do zamockowanego `set_meter_provider`, nie
    # `metrics.get_meter_provider()` (który bez mocka odzwierciedlałby ten
    # sam globalny stan, co przywraca dokładnie problem, który mockujemy).
    set_meter_provider_mock.assert_called_once()
    assert isinstance(set_meter_provider_mock.call_args[0][0], MeterProvider)


def test_setup_telemetry_pomija_start_http_server_dla_watchera_reloadera(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`manage.py runserver` bez `--noreload` i bez `RUN_MAIN=true` w env to
    proces-rodzic (watcher autoreloadera) — `setup_telemetry()` musi wrócić
    wcześnie, żeby tylko faktyczny proces serwujący ruch (dziecko,
    `RUN_MAIN=true`) bindował port 9464 (patrz komentarz w `core/telemetry.py`
    i "Blocker #1" w planie taska 14)."""
    monkeypatch.setattr(sys, "argv", ["manage.py", "runserver"])
    monkeypatch.delenv("RUN_MAIN", raising=False)
    start_http_server_mock = MagicMock()
    monkeypatch.setattr(telemetry, "start_http_server", start_http_server_mock)

    telemetry.setup_telemetry()

    start_http_server_mock.assert_not_called()


def test_setup_telemetry_nie_pomija_dziecka_reloadera_z_run_main(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Dopełnienie guardu: gdy `RUN_MAIN=true` (proces-dziecko, faktycznie
    serwujący ruch), `runserver` bez `--noreload` NIE blokuje inicjalizacji —
    inaczej telemetria nigdy by się nie uruchomiła pod `docker-compose.yml`
    (`manage.py runserver`, autoreloader domyślnie włączony).

    `set_meter_provider`/`got_request_exception` zamockowane z tego samego
    powodu, co w teście wyżej — `setup_telemetry()` idzie tu do końca funkcji
    i inaczej trwale zmutowałaby globalny stan OTel na resztę przebiegu
    `pytest`."""
    monkeypatch.setattr(sys, "argv", ["manage.py", "runserver"])
    monkeypatch.setenv("RUN_MAIN", "true")
    start_http_server_mock = MagicMock()
    monkeypatch.setattr(telemetry, "start_http_server", start_http_server_mock)
    monkeypatch.setattr(DjangoInstrumentor, "instrument", MagicMock())
    monkeypatch.setattr(telemetry.metrics, "set_meter_provider", MagicMock())
    monkeypatch.setattr(telemetry, "got_request_exception", MagicMock())

    telemetry.setup_telemetry()

    start_http_server_mock.assert_called_once_with(port=telemetry.METRICS_PORT)


def test_setup_telemetry_nie_propaguje_wyjatku_gdy_instrumentacja_pada(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """`setup_telemetry()` jest wołana synchronicznie z `CoreConfig.ready()`,
    co Django wymaga żeby się powiodło — inaczej cały proces backendu nie
    startuje. Błąd wewnątrz (tu: `DjangoInstrumentor.instrument()` rzuca) musi
    być złapany i zalogowany, nie propagowany dalej — obserwowalność nie może
    być pojedynczym punktem awarii dla aplikacji, którą ma obserwować."""
    monkeypatch.setattr(sys, "argv", ["manage.py", "test"])
    monkeypatch.delenv("RUN_MAIN", raising=False)
    monkeypatch.setattr(telemetry, "start_http_server", MagicMock())
    monkeypatch.setattr(
        DjangoInstrumentor, "instrument", MagicMock(side_effect=RuntimeError("boom"))
    )
    monkeypatch.setattr(telemetry.metrics, "set_meter_provider", MagicMock())
    monkeypatch.setattr(telemetry, "got_request_exception", MagicMock())

    with caplog.at_level("ERROR"):
        telemetry.setup_telemetry()  # nie powinno rzucić

    assert "Nie udało się zainicjalizować telemetrii OpenTelemetry" in caplog.text


def test_record_exception_dodaje_etykiety_typu_i_sciezki(monkeypatch: pytest.MonkeyPatch) -> None:
    counter_mock = MagicMock()
    monkeypatch.setattr(telemetry, "_exception_counter", counter_mock)
    request = HttpRequest()
    request.path = "/api/v1/pl/posts/"

    try:
        raise ValueError("boom")
    except ValueError:
        _record_exception(sender=None, request=request)

    counter_mock.add.assert_called_once_with(
        1, {"exception_type": "ValueError", "path": "/api/v1/pl/posts/"}
    )


def test_record_exception_bez_requestu_uzywa_sciezki_unknown(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`got_request_exception` może się odpalić bez `request` (np. wyjątek
    poza cyklem request/response) — etykieta `path` nie może wtedy wybuchnąć
    `AttributeError`, tylko spaść na wartość domyślną."""
    counter_mock = MagicMock()
    monkeypatch.setattr(telemetry, "_exception_counter", counter_mock)

    try:
        raise RuntimeError("boom")
    except RuntimeError:
        _record_exception(sender=None, request=None)

    counter_mock.add.assert_called_once_with(
        1, {"exception_type": "RuntimeError", "path": "unknown"}
    )


def test_record_db_query_mierzy_czas_i_etykietuje_operacje(monkeypatch: pytest.MonkeyPatch) -> None:
    duration_mock = MagicMock()
    monkeypatch.setattr(telemetry, "_db_query_duration", duration_mock)

    def fake_execute(sql: str, params: object, many: bool, context: dict[str, object]) -> str:
        time.sleep(0.001)
        return "wynik"

    result = _record_db_query(fake_execute, "SELECT * FROM blog_post", None, False, {})

    assert result == "wynik"
    duration_mock.record.assert_called_once()
    (duration, labels), _kwargs = duration_mock.record.call_args
    assert duration > 0
    assert labels == {"operation": "SELECT"}


def test_record_db_query_z_pustym_sql_etykietuje_unknown(monkeypatch: pytest.MonkeyPatch) -> None:
    duration_mock = MagicMock()
    monkeypatch.setattr(telemetry, "_db_query_duration", duration_mock)

    _record_db_query(lambda *a: None, "", None, False, {})

    (_duration, labels), _kwargs = duration_mock.record.call_args
    assert labels == {"operation": "UNKNOWN"}


def test_record_db_query_propaguje_wyjatek_z_execute_i_wciaz_zapisuje_czas(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`finally` w `_record_db_query` musi zadziałać nawet gdy zapytanie SQL
    faktycznie się wywala — inaczej błąd zapytania byłby "niewidzialny" dla
    metryki czasu trwania i licznik wyjątków byłby jedynym śladem po awarii
    DB, mimo że akurat ten histogram też powinien ją zarejestrować."""
    duration_mock = MagicMock()
    monkeypatch.setattr(telemetry, "_db_query_duration", duration_mock)

    def failing_execute(*_args: object) -> None:
        raise RuntimeError("db down")

    with pytest.raises(RuntimeError):
        _record_db_query(failing_execute, "UPDATE blog_post SET title = %s", None, False, {})

    duration_mock.record.assert_called_once()
    (_duration, labels), _kwargs = duration_mock.record.call_args
    assert labels == {"operation": "UPDATE"}


def test_middleware_nie_wola_execute_wrapper_gdy_otel_wylaczony(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`OTEL_METRICS_ENABLED=False` to domyślny stan w środowisku testowym —
    middleware musi być no-opem, inaczej każdy test w suicie płaciłby narzut
    `execute_wrapper` na każde zapytanie SQL."""
    from django.db import connection

    wrapper_mock = MagicMock()
    monkeypatch.setattr(connection, "execute_wrapper", wrapper_mock)
    get_response = MagicMock(return_value="response")
    middleware = DBQueryMetricsMiddleware(get_response)

    result = middleware(HttpRequest())

    assert result == "response"
    get_response.assert_called_once()
    wrapper_mock.assert_not_called()


@override_settings(OTEL_METRICS_ENABLED=True)
def test_middleware_wola_execute_wrapper_gdy_otel_wlaczony(monkeypatch: pytest.MonkeyPatch) -> None:
    from django.db import connection

    wrapper_mock = MagicMock()
    monkeypatch.setattr(connection, "execute_wrapper", wrapper_mock)
    get_response = MagicMock(return_value="response")
    middleware = DBQueryMetricsMiddleware(get_response)

    result = middleware(HttpRequest())

    assert result == "response"
    wrapper_mock.assert_called_once_with(_record_db_query)


def test_ready_nie_wola_setup_telemetry_gdy_flaga_wylaczona(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`CoreConfig.ready()` już wykonał się raz przy starcie Django dla całej
    sesji testowej (`OTEL_METRICS_ENABLED=False`, domyślne — brak `.env`/env
    var w środowisku testowym) — wołane tu ponownie explicite, żeby mieć
    bezpośredni dowód (nie tylko pośredni, przez brak `OSError: Address
    already in use` w całym suicie) że guard w `ready()` faktycznie sprawdza
    flagę przed importem/wywołaniem `setup_telemetry()`."""
    setup_mock = MagicMock()
    monkeypatch.setattr(telemetry, "setup_telemetry", setup_mock)
    config = django_apps.get_app_config("core")

    config.ready()

    setup_mock.assert_not_called()


@override_settings(OTEL_METRICS_ENABLED=True)
def test_ready_wola_setup_telemetry_gdy_flaga_wlaczona(monkeypatch: pytest.MonkeyPatch) -> None:
    setup_mock = MagicMock()
    monkeypatch.setattr(telemetry, "setup_telemetry", setup_mock)
    config = django_apps.get_app_config("core")

    config.ready()

    setup_mock.assert_called_once()
