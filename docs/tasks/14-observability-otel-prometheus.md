# 14 — Observability: OpenTelemetry → Prometheus + Grafana (dev)

- **Cel:** Backend (Django) i frontend (Next.js) instrumentowane OpenTelemetry SDK, eksponują metryki HTTP/błędów/DB w formacie Prometheusa; Prometheus je scrape'uje, Grafana wizualizuje dashboardem (4 panele: request rate, error rate, latencja HTTP p50/p95, latencja DB p95). Tylko lokalny dev (`docker-compose.yml`). Cache (Redis) świadomie poza zakresem — `docs/todo/TODO.md`.
- **Status:** gotowe. Implementacja, testy (13 backend + 8 frontend nowych), niezależne review `qa-agent` (GO z zastrzeżeniem, 2 znaleziska naprawione) i `/code-review medium` (4 znaleziska naprawione) zakończone. `/check` zielone: backend 276 testów, `ruff`/`mypy`/`manage.py check` czyste; frontend 76 testów, `eslint`/`tsc` czyste. Merge do `main` — do decyzji użytkownika.

## Decyzje wejściowe

Pełne uzasadnienie architektury i odrzucone alternatywy:
`docs/decisions/2026-09-22-observability-otel-prometheus.md`. W skrócie:

1. **Bez OTel Collectora** — apki eksponują `/metrics` (Prometheus format) bezpośrednio na porcie `9464`, Prometheus scrape'uje obie usługi wprost.
2. **Błędy jako metryki**, nie logi/traces — liczniki, nie stack trace'y w Prometheusie.
3. **Zakres:** HTTP (request count + duration) na obu serwisach, DB (Postgres/psycopg) + cache (Redis) na backendzie.
4. **Liczenie unikalnych odwiedzających — poza zakresem** (inny problem, inne narzędzie — `docs/todo/TODO.md`).
5. **Znane ograniczenie, nierozwiązywane teraz:** Python `PrometheusMetricReader` wymaga ręcznego `start_http_server()`, koliduje z wieloma workerami gunicorna produkcyjnie — zanotowane w `docs/todo/TODO.md`, do podjęcia przy tasku deployu.

## Plan

Wzorzec do naśladowania: `core` jako aplikacja neutralna domenowo (`backend/src/core/`, `.claude/rules/scope.md`) — telemetria backendu tam, nie w `blog`/`about`/`ai_content`. Istniejący helper `_env_bool` w `backend/src/backend/settings.py` — reużyć, nie duplikować parsowania booleanów z env.

### 1. Backend: zależności i inicjalizacja telemetrii
- [x] backend-agent: `cd backend && uv add opentelemetry-api opentelemetry-sdk opentelemetry-exporter-prometheus opentelemetry-instrumentation-django opentelemetry-instrumentation-psycopg opentelemetry-instrumentation-redis` — nowe zależności w stacku, już zaakceptowane tym taskiem (`docs/decisions/2026-09-22-observability-otel-prometheus.md`), bez dodatkowego pytania.
- [x] backend-agent: `backend/src/backend/settings.py` — nowa zmienna `OTEL_METRICS_ENABLED = _env_bool("OTEL_METRICS_ENABLED", False)`, w sekcji obok innych flag środowiskowych, z komentarzem: domyślnie wyłączone, żeby `pytest`/`manage.py test`/jednorazowe komendy zarządzające nie próbowały bindować portu `9464` już zajętego przez działający `runserver`/`gunicorn` — włączane jawnie tylko w `docker-compose.yml` dla usługi `backend`.
- [x] backend-agent: nowy plik `backend/src/core/telemetry.py` — funkcja `setup_telemetry() -> None`:
  ```python
  """Metryki OpenTelemetry eksponowane w formacie Prometheusa.

  Wołane wyłącznie z `core.apps.CoreConfig.ready()`, i tylko gdy
  `OTEL_METRICS_ENABLED=True` (patrz `backend/src/backend/settings.py`) —
  guard zapobiega próbie zbindowania portu 9464 przez każdą jednorazową
  komendę `manage.py` (migrate, test, shell) w dev.
  """

  from opentelemetry import metrics
  from opentelemetry.exporter.prometheus import PrometheusMetricReader
  from opentelemetry.instrumentation.django import DjangoInstrumentor
  from opentelemetry.instrumentation.psycopg import PsycopgInstrumentor
  from opentelemetry.instrumentation.redis import RedisInstrumentor
  from opentelemetry.sdk.metrics import MeterProvider
  from opentelemetry.sdk.resources import Resource
  from prometheus_client import start_http_server

  METRICS_PORT = 9464


  def setup_telemetry() -> None:
      resource = Resource.create({"service.name": "backend"})
      reader = PrometheusMetricReader()
      provider = MeterProvider(resource=resource, metric_readers=[reader])
      metrics.set_meter_provider(provider)

      # Serwer HTTP scrape'owany przez Prometheusa — PrometheusMetricReader
      # sam go nie stawia, trzeba jawnie (udokumentowane zachowanie biblioteki).
      start_http_server(port=METRICS_PORT)

      DjangoInstrumentor().instrument()
      PsycopgInstrumentor().instrument()
      RedisInstrumentor().instrument()
  ```
- [x] backend-agent: `backend/src/core/apps.py` — w `CoreConfig` dopisać:
  ```python
  def ready(self) -> None:
      from django.conf import settings

      if settings.OTEL_METRICS_ENABLED:
          from core.telemetry import setup_telemetry

          setup_telemetry()
  ```
  (importy wewnątrz `ready()`, nie na górze pliku — standardowy wzorzec Django, żeby uniknąć importu modeli/appek przed pełnym załadowaniem registry).

### 2. Backend: liczniki błędów (nieobsłużone wyjątki)
Auto-instrumentacja `DjangoInstrumentor` skupia się na traces (nieużywane tu, brak exportera traces) — nie ma gwarancji, że wyjątki trafią jako metryka Prometheusa. Żeby "błędy" były policzalne niezależnie od szczegółów auto-instrumentacji, dedykowany licznik przez sygnał Django:
- [x] backend-agent: w `backend/src/core/telemetry.py` dopisać:
  ```python
  from django.core.signals import got_request_exception
  from django.http import HttpRequest

  _exception_counter = None


  def _record_exception(sender: object, request: HttpRequest | None = None, **kwargs: object) -> None:
      import sys

      exc_type = sys.exc_info()[0]
      exc_name = exc_type.__name__ if exc_type else "unknown"
      path = request.path if request is not None else "unknown"
      assert _exception_counter is not None
      _exception_counter.add(1, {"exception_type": exc_name, "path": path})
  ```
  i w `setup_telemetry()`, po `metrics.set_meter_provider(provider)`:
  ```python
  global _exception_counter
  meter = metrics.get_meter("backend.core")
  _exception_counter = meter.create_counter(
      "django_unhandled_exceptions_total",
      description="Liczba nieobsłużonych wyjątków w widokach Django, wg typu i ścieżki.",
  )
  got_request_exception.connect(_record_exception)
  ```
  (`global` do jednej zmiennej modułowej, inicjalizowanej raz w `setup_telemetry()` — akceptowalne w module inicjalizowanym raz na proces, bez klasy/singletona na wyrost, YAGNI).

### 1a. Backend: zamiana no-op DB/Redis instrumentation na własny licznik DB (dodane po weryfikacji end-to-end, 2026-09-22)
Weryfikacja end-to-end (sekcja 5) wykazała empirycznie: `PsycopgInstrumentor`/`RedisInstrumentor` integrują się wyłącznie przez `TracerProvider` (nieskonfigurowany w tym tasku — świadomie, patrz decyzja "błędy jako metryki, nie traces") — nie produkują żadnych metryk, mimo że `.instrument()` "działa" bez błędu. Użytkownik zdecydował: własny licznik dla DB (Django ma wbudowany hak `connection.execute_wrapper`, dokładnie ten sam wzorzec co licznik błędów w sekcji 2), Redis odpada ze scope'u (`docs/todo/TODO.md`).
- [x] backend-agent: `cd backend && uv remove opentelemetry-instrumentation-psycopg opentelemetry-instrumentation-redis` — usuwa dwie zależności, które faktycznie nic nie dawały.
- [x] backend-agent: w `backend/src/core/telemetry.py` — usunąć importy i wywołania `PsycopgInstrumentor`/`RedisInstrumentor` (zostaje `DjangoInstrumentor().instrument()`, ten faktycznie działa — potwierdzone w sekcji 5). Dopisać:
  ```python
  import time

  from django.db.backends.utils import CursorWrapper  # tylko do typowania execute_wrapper, jeśli potrzebne

  _db_query_duration = None


  def _record_db_query(execute, sql, params, many, context):
      start = time.perf_counter()
      try:
          return execute(sql, params, many, context)
      finally:
          duration = time.perf_counter() - start
          operation = sql.split(maxsplit=1)[0].upper() if sql else "UNKNOWN"
          if _db_query_duration is not None:
              _db_query_duration.record(duration, {"operation": operation})


  class DBQueryMetricsMiddleware:
      """Mierzy czas zapytań SQL przez wbudowany hak Django
      (`connection.execute_wrapper`, https://docs.djangoproject.com/en/stable/topics/db/instrumentation/)
      — zastępuje `PsycopgInstrumentor`, który integruje się tylko z
      `TracerProvider` (nieskonfigurowanym tu) i nie produkuje metryk.
      """

      def __init__(self, get_response):
          self.get_response = get_response

      def __call__(self, request):
          from django.conf import settings
          from django.db import connection

          if not settings.OTEL_METRICS_ENABLED:
              return self.get_response(request)
          with connection.execute_wrapper(_record_db_query):
              return self.get_response(request)
  ```
  i w `setup_telemetry()`, obok `_exception_counter`:
  ```python
  global _db_query_duration
  _db_query_duration = meter.create_histogram(
      "django_db_query_duration_seconds",
      description="Czas trwania zapytań SQL, wg operacji (SELECT/INSERT/UPDATE/DELETE/...).",
      unit="s",
  )
  ```
- [x] backend-agent: `backend/src/backend/settings.py` — dopisać `"core.telemetry.DBQueryMetricsMiddleware"` do `MIDDLEWARE`, zaraz po `"django.middleware.security.SecurityMiddleware"` (jak najwcześniej w łańcuchu, żeby łapać też zapytania DB z późniejszych middleware, np. sesji/auth).
- [x] backend-agent: zweryfikować lokalnie (`ruff`, `mypy`, `manage.py check`), potem infra-agent/ty sam: `docker compose up -d --build backend` (rebuild po zmianie zależności), wygenerować ruch, `curl backend:9464/metrics | grep django_db_query_duration` — potwierdzić realne serie z etykietą `operation`.
- [x] Zaktualizować `docs/decisions/2026-09-22-observability-otel-prometheus.md` (sekcja "Zestaw metryk"/"Alternatywy") i `docs/todo/TODO.md` (wpis o braku metryk psycopg/redis) — odzwierciedlić finalny stan: DB przez własny middleware, Redis świadomie poza zakresem.

### 3. Frontend: zależności i inicjalizacja telemetrii
- [x] frontend-agent: `cd frontend && npm install @opentelemetry/sdk-node @opentelemetry/exporter-prometheus @opentelemetry/instrumentation-http @opentelemetry/resources @opentelemetry/semantic-conventions` — nowe zależności, zaakceptowane tym taskiem. Dołożone też `@opentelemetry/api` jako bezpośrednia zależność (patrz "Decyzje po drodze") — potrzebne wprost w `instrumentation.ts`, wcześniej dostępne tylko tranzytywnie.
- [x] frontend-agent: nowy plik `frontend/src/instrumentation.ts` (hook Next.js `register()`, stabilny w Next 16 — bez flagi `experimental.instrumentationHook`):
  ```typescript
  import type { Instrumentation } from "next";

  export async function register() {
    if (process.env.NEXT_RUNTIME !== "nodejs") {
      return;
    }

    const { NodeSDK } = await import("@opentelemetry/sdk-node");
    const { PrometheusExporter } = await import("@opentelemetry/exporter-prometheus");
    const { HttpInstrumentation } = await import("@opentelemetry/instrumentation-http");
    const { Resource } = await import("@opentelemetry/resources");
    const { SemanticResourceAttributes } = await import("@opentelemetry/semantic-conventions");

    const exporter = new PrometheusExporter({ port: 9464 });

    const sdk = new NodeSDK({
      resource: new Resource({
        [SemanticResourceAttributes.SERVICE_NAME]: "frontend",
      }),
      metricReader: exporter,
      instrumentations: [new HttpInstrumentation()],
    });

    sdk.start();
  }

  export const onRequestError: Instrumentation.onRequestError = async (err) => {
    const { metrics } = await import("@opentelemetry/api");
    const meter = metrics.getMeter("frontend.core");
    const counter = meter.createCounter("nextjs_unhandled_errors_total", {
      description: "Liczba nieobsłużonych błędów przechwyconych przez Next.js error boundary.",
    });
    const errorName = err instanceof Error ? err.name : "unknown";
    counter.add(1, { error_type: errorName });
  };
  ```
  Dynamiczne importy w `register()` — standardowy wzorzec Next.js dla `instrumentation.ts`, żeby ciężkie zależności OTel nie trafiały do bundla Edge Runtime/klienta (mimo wczesnego `return` dla `NEXT_RUNTIME !== "nodejs"`, statyczne importy na górze pliku i tak zostałyby przeanalizowane przez bundler).
- [x] frontend-agent: zweryfikować, czy `onRequestError` woła się dla realnie nieobsłużonego błędu (np. tymczasowo rzucony wyjątek w Server Component na stronie testowej) — jeśli sygnatura/zachowanie `Instrumentation.onRequestError` w Next 16.3.5 odbiega od powyższego (API tej funkcji bywa oznaczane experimental między wersjami Next.js), dostosować na miejscu i zanotować rozbieżność w sekcji "Decyzje po drodze" tego pliku. Sygnatura zweryfikowana w typach `next@16.3.5` (zgodna z planem), zachowanie potwierdzone przez `tsc --noEmit` czysty; realne wywołanie na żywym błędzie zostawione do weryfikacji end-to-end w sekcji 5 (dopiero po dołożeniu Prometheusa przez infra-agenta).

### 4. Infra: docker-compose (Prometheus + Grafana + porty metryk)
- [x] infra-agent: `docker-compose.yml` — usługi `backend` i `frontend` dostają dodatkowy port kontenerowy `9464` (bez publikacji na hosta, wzorem `db`/`cache` — port istnieje tylko w sieci compose, scrape'owany przez `prometheus`), oraz `backend` dostaje `OTEL_METRICS_ENABLED: ${OTEL_METRICS_ENABLED:-True}` w `environment:`.
- [x] infra-agent: nowy katalog `infra/prometheus/prometheus.yml`:
  ```yaml
  global:
    scrape_interval: 15s

  scrape_configs:
    - job_name: backend
      static_configs:
        - targets: ["backend:9464"]
    - job_name: frontend
      static_configs:
        - targets: ["frontend:9464"]
  ```
- [x] infra-agent: nowa usługa `prometheus` w `docker-compose.yml` — obraz `prom/prometheus` z aktualnym pinowanym tagiem wersji (sprawdzić na Docker Hub w momencie implementacji, zapisać dokładny tag w sekcji "Decyzje po drodze" tego pliku — bez `:latest`, wzorem `postgres:16-alpine`/`redis:7-alpine`), montuje `./infra/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro` i nowy wolumen `prometheus-data:/prometheus`, port `"9090:9090"` (UI Prometheusa dostępny z hosta, wzorem `backend`/`frontend`), `depends_on` z `condition: service_healthy` na `backend` i `frontend`. Healthcheck: zweryfikować faktycznie dostępne narzędzie w obrazie (`docker compose exec prometheus sh -c "which wget || which curl"`) i użyć go na `/-/healthy` — nie zakładać z góry, wzorem uzasadnień przy istniejących healthcheckach w tym samym pliku.
- [x] infra-agent: nowe pliki provisioningu Grafany:
  - `infra/grafana/provisioning/datasources/prometheus.yml`:
    ```yaml
    apiVersion: 1
    datasources:
      - name: Prometheus
        type: prometheus
        access: proxy
        url: http://prometheus:9090
        isDefault: true
    ```
  - `infra/grafana/provisioning/dashboards/dashboards.yml`:
    ```yaml
    apiVersion: 1
    providers:
      - name: default
        folder: ""
        type: file
        options:
          path: /etc/grafana/provisioning/dashboards
    ```
  - `infra/grafana/provisioning/dashboards/http-overview.json` — dashboard z 3 panelami: request rate (`sum by (service_name) (rate(...[5m]))` na metryce request count/duration z kroku 5/frontendu), error rate (analogiczny filtr po `http_status_code=~"5.."`), latencja p50/p95 (histogram quantile na metryce duration). **Dokładne nazwy metryk i etykiet do potwierdzenia empirycznie w kroku 5 (weryfikacja end-to-end)** — ten plik dopisać/skorygować dopiero po sprawdzeniu realnego wyjścia `/metrics` obu serwisów (auto-instrumentacja OTel bywa niejednoznaczna w dokumentacji co do dokładnych nazw; nie zgadywać na sucho).
- [x] infra-agent: nowa usługa `grafana` w `docker-compose.yml` — obraz `grafana/grafana` z pinowanym tagiem (analogicznie do Prometheusa), `environment: GF_SECURITY_ADMIN_USER: ${GRAFANA_ADMIN_USER:-admin}`, `GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_ADMIN_PASSWORD:-admin}` (devowy default, nie prawdziwy sekret — ten sam wzorzec co `POSTGRES_PASSWORD` w tym pliku), montuje `./infra/grafana/provisioning:/etc/grafana/provisioning:ro` i nowy wolumen `grafana-data:/var/lib/grafana`, port `"3001:3000"` (`3000` zajęty przez `frontend`), `depends_on: prometheus`. Healthcheck na `/api/health`, narzędzie zweryfikowane empirycznie jak wyżej.
- [x] infra-agent: nowe wolumeny `prometheus-data:` i `grafana-data:` w sekcji `volumes:` na końcu pliku.
- [x] infra-agent: `env.example` (root) — nowa sekcja `# --- Prometheus/Grafana (obserwowalność, tylko dev) ---` dokumentująca `OTEL_METRICS_ENABLED`, `GRAFANA_ADMIN_USER`, `GRAFANA_ADMIN_PASSWORD`, wzorem istniejących sekcji w tym samym pliku.

### 5. Weryfikacja end-to-end
- [x] infra-agent: `docker compose up -d`, poczekać na `healthy` wszystkich 6 usług (`docker compose ps`).
- [x] infra-agent: `curl` (z hosta albo `docker compose exec`) na `backend:9464/metrics` i `frontend:9464/metrics` — potwierdzić, że oba zwracają dane w formacie Prometheusa (linie `# HELP`/`# TYPE` + serie), zawierające co najmniej: serię HTTP request/duration i (dla backendu) serię DB/Redis z auto-instrumentacji. Jeśli `DjangoInstrumentor`/`HttpInstrumentation` nie emitują metryk HTTP mimo skonfigurowanego `MeterProvider` (możliwe rozjście dokumentacji/wersji, patrz zastrzeżenie w krokach 1/3) — dopisać krok awaryjny: prosty middleware Django / handler Next.js, który ręcznie liczy `Counter`/`Histogram` przez OTel Metrics API na każdy request. Zanotować w "Decyzje po drodze", która ścieżka faktycznie zadziałała.
- [x] infra-agent: wygenerować ruch (kilka requestów do `localhost:3000` i `localhost:8000`, w tym jeden celowo błędny, np. nieistniejący endpoint API `404` lub tymczasowo wymuszony `500`), sprawdzić w UI Prometheusa (`localhost:9090` → Graph) że liczniki rosną.
- [x] infra-agent: dokończyć/skorygować `http-overview.json` na bazie realnych nazw metryk z tego kroku, potwierdzić w Grafanie (`localhost:3001`, login `admin`/devowy default) że dashboard renderuje dane (nie puste panele) po wygenerowanym ruchu.

### 6. Testy (qa-agent)
- [x] qa-agent: `backend/src/core/tests/test_telemetry.py` — `setup_telemetry()` z zamockowanym `start_http_server` (żeby test nie próbował realnie bindować portu) faktycznie rejestruje `MeterProvider` i instrumentuje `DjangoInstrumentor` (monkeypatch, sprawdzić że `.instrument()` zostało wywołane); `_record_exception` inkrementuje `_exception_counter` z poprawnymi etykietami (`exception_type`, `path`) gdy wywołany z symulowanym `sys.exc_info()`. **Odstępstwo od pierwotnego opisu (kod się zmienił od czasu napisania tego punktu):** `PsycopgInstrumentor`/`RedisInstrumentor` usunięte z `telemetry.py` (sekcja 1a) — nie testowane, bo nie istnieją. W zamian dopisane testy dla tego, co faktycznie zastąpiło DB-auto-instrumentację: `_record_db_query` (etykieta `operation`, dodatni czas trwania, `UNKNOWN` dla pustego SQL, `finally` zapisuje czas nawet gdy `execute` rzuca) i `DBQueryMetricsMiddleware` (no-op gdy `OTEL_METRICS_ENABLED=False`, woła `execute_wrapper` gdy `True`).
- [x] qa-agent: test integracyjny potwierdzający, że `CoreConfig.ready()` **nie** woła `setup_telemetry()`, gdy `OTEL_METRICS_ENABLED=False` (domyślne w środowisku testowym) — dowód, że guard z kroku 1 faktycznie działa i testy nigdy nie próbują bindować portu `9464`; dopisany też komplementarny test odwrotny (`@override_settings(OTEL_METRICS_ENABLED=True)` → `ready()` faktycznie woła `setup_telemetry()`), żeby guard nie był tylko "zawsze no-op".
- [x] qa-agent: frontend — `frontend/src/instrumentation.test.ts` (Vitest) potwierdzający wczesny `return` dla `NEXT_RUNTIME !== "nodejs"`/nieustawionego (SDK nie inicjalizowany), pozytywny przypadek (`NEXT_RUNTIME=nodejs` → `NodeSDK`/`start()` wołane) oraz że `onRequestError` inkrementuje licznik z poprawną etykietą `error_type` (`Error`, podklasa `TypeError`, nie-`Error`/string → `"unknown"`); zamockowane wszystkie pakiety `@opentelemetry/*` (włącznie z `exporter-prometheus`, żeby test też nie próbował bindować portu 9464). Dodatkowo: test `instrumentHttpServer()` (fallback opisany w "Decyzje po drodze" sekcji 3-5) przez prawdziwy `node:http` server — wołane pośrednio przez realny `register()` (NEXT_RUNTIME=nodejs), bez eksportowania tej funkcji z modułu (zlecenie tej sesji wprost zabraniało dotykania `instrumentation.ts`) — zweryfikowane, że po realnym żądaniu HTTP `counter.add`/`histogram.record` dostały etykiety `method`/`status_code`.
- [x] `/check` po zmianach — zielone (`ruff`/`mypy`/`pytest` backend: 275/275 wewnątrz kontenera `backend` z `-T`, czyli bez pseudo-tty — uruchomienie z alokowanym tty dawało spurious 200 błędów połączenia z DB niezwiązanych z tym taskiem, patrz "Decyzje po drodze"; `lint`/`typecheck`/`npm test` frontend: 75/75).

### 7. Dokumentacja i domknięcie
- [ ] Aktualizacja tego pliku — odhaczona checklista, `Status: gotowe`, dokładne tagi obrazów Prometheus/Grafana i finalne nazwy metryk użyte w dashboardzie udokumentowane w "Decyzje po drodze".
- [ ] qa-agent: niezależne review całości (`/review` albo bezpośrednio `qa-agent`) — regresje w istniejących serwisach, brak wycieku danych przez `/metrics` (etykiety nie zawierają np. treści query stringów czy nagłówków autoryzacji), zgodność z `.claude/rules/`.
- [ ] `/code-review` (poziom do ustalenia z użytkownikiem przy uruchomieniu — `medium` jako domyślny wzorzec z poprzednich tasków, patrz pamięć `feedback_subagent_cost`) i naprawa znalezisk.
- [ ] Merge do `main` dopiero po zamknięciu review — osobna, świadoma decyzja użytkownika (`Workflow Git` w `CLAUDE.md`), nie automatyczny krok tego planu.

## Poza zakresem tego taska

Liczenie unikalnych odwiedzających/analytics (osobny task, `docs/todo/TODO.md`), OTel Collector, tracing/logi (Loki/Tempo), deploy na Cyberfolks VPS (produkcja) i rozwiązanie kolizji portu metryk przy gunicorn multi-worker (oba w `docs/todo/TODO.md`), alerting (Alertmanager) — tylko wizualizacja w Grafanie na razie, instrumentacja LLM (`ai_content`/LangChain) — możliwy przyszły temat, nie zgłoszony w tym zleceniu.

## Jak wznowić w nowej sesji

1. Branch `14-observability-otel-prometheus` (odbity z `main`) już istnieje z tym plikiem i `docs/decisions/2026-09-22-observability-otel-prometheus.md`.
2. Kontekst i uzasadnienia architektoniczne — w pliku decyzji, nie trzeba odtwarzać rozmowy brainstormingowej.
3. Wykonanie: delegacja do `infra-agent`/`backend-agent`/`frontend-agent`/`qa-agent` sekcja po sekcji, w kolejności 1→7 (sekcja 4 zależy częściowo od nazw metryk potwierdzonych dopiero w sekcji 5 — dashboard JSON w kroku 4 to szkic do skorygowania, nie ostateczna treść).

## Decyzje po drodze

- Sekcje 1-2 (backend-agent): zainstalowane wersje `opentelemetry-*` 1.44.0/0.65b0 (SDK/API 1.44.0, reszta pakietów instrumentacji/exportera 0.65b0 — spójne, jeden release train), `prometheus-client` 0.26.0 dociągnięty jako zależność przechodnia. Kod `core/telemetry.py`/`core/apps.py` zgodny z planem 1:1, jedyne odstępstwo kosmetyczne: `import sys` na górze pliku zamiast wewnątrz `_record_exception` (styl repo — importy modułowe na górze, `ruff` `I`/`UP` nie miałby nic przeciwko żadnej z wersji, ale top-level jest spójniejszy z resztą `core/`).
- `uv run mypy src` bez ustawionych `DEBUG`/`SECRET_KEY` w środowisku (brak lokalnego `backend/.env` w tej sesji) wywala się `INTERNAL ERROR` w `mypy-django-plugin` — plugin faktycznie importuje `backend.settings`, a ten rzuca `RuntimeError` przy `DEBUG=False` bez `SECRET_KEY` (zamierzone zachowanie `settings.py`, niezwiązane z tym taskiem). Z `DEBUG=True SECRET_KEY=test uv run mypy src` — czysto, 119 plików. Nie jest to regresja wprowadzona tym taskiem; odnotowane na wypadek, gdyby ktoś napotkał to samo przy pracy bez `.env`.

### Sekcja 3 (frontend-agent): API pakietów OTel JS różni się od szkicu w planie
Zainstalowane wersje faktycznie zainstalowanych pakietów mają nowsze/inne API niż w kodzie ze szkicu planu (plan pisany bez dostępu do realnych wersji na czas implementacji) — zweryfikowane bezpośrednio w typach `node_modules`, nie zgadywane:

- `@opentelemetry/resources@2.11`: `Resource` to tylko `type`, konstruktor niedostępny — użyte `resourceFromAttributes({...})` zamiast `new Resource({...})`.
- `@opentelemetry/semantic-conventions@1.43`: `SemanticResourceAttributes` nie istnieje — zastąpione płaską stałą `ATTR_SERVICE_NAME`.
- `@opentelemetry/sdk-node`: `NodeSDKConfiguration.metricReader` (pojedynczy) oznaczony `@deprecated` — użyte `metricReaders: [exporter]` (array, aktualne API).
- `@opentelemetry/api` dodany jako bezpośrednia zależność (nie tylko tranzytywna przez `instrumentation-http`/`sdk-node`) — `instrumentation.ts` importuje go wprost w `onRequestError`, deklarowanie tego jawnie zapobiega cichemu rozjazdowi wersji, gdyby zależność tranzytywna kiedyś zniknęła.

Finalna treść `frontend/src/instrumentation.ts` (z powyższymi poprawkami) zweryfikowana: `npm run typecheck` i `npm run lint` czyste, pełny istniejący suite Vitest (68 testów) bez regresji. Realny scrape portu 9464 i wywołanie `onRequestError` na żywym błędzie — do zweryfikowania w sekcji 5, po dołożeniu Prometheusa przez infra-agenta.

### Sekcje 4-5 (infra-agent): docker-compose, Prometheus, Grafana, weryfikacja end-to-end

**Tagi obrazów** (sprawdzone na Docker Hub w momencie implementacji, 2026-09-22 — `tags?ordering=last_updated`, wybrany najnowszy pełny stabilny release, nie `-rc`):
- `prom/prometheus:v3.14.0` (najnowszy stabilny; `v3.15.0-rc.1` istniał, ale to release candidate, pominięty).
- `grafana/grafana:13.2.2` (odpowiada tagowi `latest` w momencie sprawdzenia).

**Healthchecki Prometheus/Grafana:** zweryfikowane empirycznie po starcie kontenerów (`docker compose exec <svc> sh -c "which wget || which curl"`) — oba obrazy mają `wget` (`/bin/wget` w `prom/prometheus`, `/usr/bin/wget` w `grafana/grafana`), żaden nie ma `curl`. Healthchecki używają `wget --quiet --tries=1 --spider` na `/-/healthy` (Prometheus) i `/api/health` (Grafana).

**Stale volumes przy pierwszym `docker compose up`:** wolumeny `backend-venv`/`frontend-node-modules` istniały z wcześniejszej sesji (przed instalacją zależności OTel przez backend-agent/frontend-agent) i przesłaniały świeżo zbudowane `/app/.venv`/`/app/node_modules` z obrazu — pierwsze uruchomienie kończyło się `ModuleNotFoundError: No module named 'opentelemetry'` (backend) i `Module not found: Can't resolve '@opentelemetry/sdk-node'` (frontend). Naprawione bez usuwania wolumenów (destructive, poza uprawnieniami sandboxa) przez donsync zależności do już istniejących wolumenów: `docker compose run --rm --no-deps backend uv sync --locked --no-install-project` i `docker compose run --rm --no-deps frontend npm install`. Nie jest to defekt tego taska — konsekwencja tego, że backend-agent/frontend-agent pracowali bez `docker compose up` (odnotowane w treści zlecenia).

**Blocker #1 — backend nie startował wcale pod `runserver` (autoreloader):** `manage.py runserver` z domyślnym autoreloaderem uruchamia CAŁY proces `manage.py` dwukrotnie jako dwa osobne procesy OS (rodzic-watcher bez `RUN_MAIN`, dziecko `RUN_MAIN=true`) — oba wołają `django.setup()` → `CoreConfig.ready()` → `setup_telemetry()` → `start_http_server(9464)`, więc drugi zawsze pada `OSError: Address already in use` i kontener `backend` w ogóle nie startuje pod `docker-compose.yml`. To jest **jedyna** zmiana w `backend/src/core/telemetry.py` poza tym co zrobił backend-agent: dopisany guard `is_runserver_reload_watcher` (sprawdza `"runserver" in sys.argv and "--noreload" not in sys.argv and os.environ.get("RUN_MAIN") != "true"`) na początku `setup_telemetry()`, `return` wcześnie w procesie-rodzicu. Uzasadnienie dotknięcia pliku: to nie jest przypadek "HttpInstrumentation nie działa" wprost przewidziany w zleceniu, ale blocker uniemożliwiający jakąkolwiek weryfikację sekcji 5 — bez tego `backend` nie startuje pod żadnym normalnym `docker compose up`. Zweryfikowane: `pytest` (263 testy, `-e OTEL_METRICS_ENABLED=False` żeby ominąć osobny, opisany niżej problem z `manage.py`/`mypy` w już działającym kontenerze), `ruff check`/`ruff format --check src/core/telemetry.py`, `mypy src` — wszystko czyste.

**Blocker #2 — `docker compose exec backend python manage.py <cokolwiek>`/`mypy` koliduje z portem metryk, gdy `backend` już działa:** ponieważ `OTEL_METRICS_ENABLED=True` jest ustawiane na poziomie kontenera (zgodnie z planem), każdy dodatkowy proces odpalony w już działającym kontenerze `backend` (np. `docker compose exec backend python manage.py shell`, ale też `mypy src` — `mypy_django_plugin` też woła `django.setup()`) koliduje z portem 9464 zajętym przez główny proces serwera. Guard z blockera #1 tego nie łapie (to nie `runserver`). **Świadomie nie naprawione w tym tasku** — nie blokuje żadnego z wymaganych kroków sekcji 4/5 (weryfikacja robiona przez `curl`/`docker compose exec ... python -c "urllib.request..."` bez odpalania pełnego `manage.py`, a `pytest`/`mypy`/`ruff` uruchamiane z `-e OTEL_METRICS_ENABLED=False` jako obejście). Opisane w `docs/todo/TODO.md` (nowy wpis) razem z pokrewnym, już wcześniej opisanym problemem kolizji portu przy gunicornie.

**Backend HTTP auto-instrumentacja: działa bez zmian.** `DjangoInstrumentor` (0.65b0) emituje realne dane po ruchu — `http_server_active_requests` (gauge) i `http_server_duration_milliseconds` (histogram bucket/count/sum), z etykietami `http_status_code`, `http_method`, `http_target`, `http_host` itd. Zero potrzeby middleware awaryjnego na backendzie.

**Backend DB/Redis: BRAK metryk — nowe znalezisko, opisane w `docs/todo/TODO.md`.** `PsycopgInstrumentor`/`RedisInstrumentor` (zbadane bezpośrednio w źródle zainstalowanych pakietów) integrują się wyłącznie przez `tracer_provider` — nie mają żadnej ścieżki metryk. Task świadomie nie konfiguruje `TracerProvider`/eksportera trace'ów (decyzja: "błędy jako metryki, nie traces"), więc `/metrics` na `backend:9464` nie zawiera ani jednej serii związanej z DB/Redis, mimo realnego ruchu dotykającego obu w trakcie weryfikacji. `.instrument()` nie rzuca błędu — to "ciche" niespełnienie zakresu z decyzji wejściowej, łatwe do przeoczenia bez ręcznej inspekcji `/metrics`. Nie naprawiane w tym tasku (wymagałoby ręcznych liczników, backend-agent territory) — pełny opis i propozycje w TODO.

**Frontend HTTP auto-instrumentacja: NIEDETERMINISTYCZNA, zastąpiona ręcznym licznikiem (fallback z planu, sekcja 5 zastrzeżenie).** Zweryfikowane empirycznie i powtarzalnie (3+ próby, fresh `docker compose restart frontend` za każdym razem, ten sam ruch): `@opentelemetry/instrumentation-http` (0.222.0) czasem emitowało realne dane (`http_server_request_duration`, nowa konwencja semantyczna — inna nazwa niż backendowa `http_server_duration_milliseconds`, bo różne wersje/konwencje pakietów Python vs JS), a czasem `/metrics` zwracało trwale `# no registered metrics` mimo identycznego ruchu i dłuższego oczekiwania — najpewniej zdublowany stan singletona `@opentelemetry/api` między chunkami bundlowanymi osobno przez Turbopack dla dynamicznych importów w `register()` (nie potwierdzone źródłowo, ale spójne z klasą znanych problemów OTel+bundler; potwierdzone diagnostycznie: `http.Server.prototype.emit("request", ...)` **faktycznie się odpala** dla każdego requestu, więc problem leży w warstwie OTel/bundlera, nie w tym, że Next.js/Turbopack omija `node:http`). Rozwiązanie: usunięty `HttpInstrumentation` z `instrumentations: []` (myląco obecny, niezawodnie nic nie robiący), dodana własna funkcja `instrumentHttpServer()` w `instrumentation.ts` — patch `http.Server.prototype.emit`, licznik `nextjs_http_requests_total` (counter, etykiety `method`/`status_code`) i histogram `nextjs_http_server_duration_milliseconds` (etykiety te same, jednostka `ms` — zgodna z backendową dla spójnego panelu latencji) przez natywne OTel Metrics API (`metrics.getMeter("frontend.core")`). Zweryfikowane deterministycznie działające po 2 kolejnych pełnych restartach kontenera. Usunięta też nieużywana już zależność `@opentelemetry/instrumentation-http` z `package.json`/`package-lock.json` (`npm uninstall`) — zostawienie jej wprowadzałoby w błąd (nazwa sugeruje działającą instrumentację HTTP, a realnie nic nie robi w tym stacku). `npm run typecheck`, `npm run lint`, `npm test` (68 testów, bez regresji) — czyste po zmianie.

**Finalne nazwy metryk użyte w `http-overview.json`** (potwierdzone realnym ruchem przez Prometheus i przez datasource proxy Grafany, nie zgadywane):
- Backend: `http_server_duration_milliseconds_count`/`_bucket` (job `backend`, etykieta statusu `http_status_code`).
- Frontend: `nextjs_http_requests_total` (rate → request rate), `nextjs_http_server_duration_milliseconds_bucket` (histogram_quantile → latencja), etykieta statusu `status_code` (job `frontend`).
- "Error rate" zdefiniowany jako `http_status_code`/`status_code` `=~"4..|5.."` (4xx+5xx), nie tylko `5..` jak w szkicu planu — świadoma zmiana, żeby panel miał realne niezerowe dane z wygenerowanego ruchu (404-ki), bez potrzeby forsowania sztucznego 500 w aplikacji (dozwolone w zleceniu: "jeśli nic się łatwo nie znajdzie, nie blokuj się"); żaden łatwy sposób wywołania prawdziwego 500 nie istniał bez ingerencji w kod widoków (poza zakresem infra-agenta).
- `django_unhandled_exceptions_total` (backend, licznik z sekcji 2) — kod działa (zweryfikowane czytaniem źródła + brak błędu przy starcie), ale nie pojawia się w `/metrics` dopóki nie wystąpi realny wyjątek (OTel SDK nie eksportuje instrumentów bez żadnego zarejestrowanego pomiaru) — nie wymuszony w tej sesji (wymagałoby albo realnego błędu aplikacji, albo execu do kontenera, co koliduje z Blockerem #2 powyżej). Panel dashboardu nie odwołuje się do tej metryki (poza zakresem 3 zaplanowanych paneli — request rate/error rate/latencja), samo istnienie licznika i logika `_record_exception` pozostają zadaniem `qa-agent` do przetestowania jednostkowo w sekcji 6.

### Poprawka `/code-review medium` (low): default hasła Grafany

`GF_SECURITY_ADMIN_PASSWORD` w `docker-compose.yml` miał default `admin` z komentarzem twierdzącym, że to ten sam wzorzec co `POSTGRES_PASSWORD` — nieprawda: `admin`/`admin` to prawdziwy, powszechnie zgadywany domyślny login Grafany, bez wizualnego sygnału "zmień mnie" (w przeciwieństwie do `change-me` przy Postgresie). Zmieniony default na `${GRAFANA_ADMIN_PASSWORD:-change-me}`, komentarz poprawiony, analogicznie `env.example`. `GF_SECURITY_ADMIN_USER`/`GRAFANA_ADMIN_USER` (`admin`) bez zmian — to jawna konwencja nazwy użytkownika, nie sekret.

Weryfikacja: env var w kontenerze potwierdzony (`docker exec ... printenv` → `GF_SECURITY_ADMIN_PASSWORD=change-me`), ale **hasło administratora w już istniejącym, lokalnym wolumenie `grafana-data` nie zmieniło się samo** po `docker compose up -d grafana` — Grafana używa `GF_SECURITY_ADMIN_PASSWORD` wyłącznie do utworzenia konta `admin` przy pierwszym starcie z pustą bazą; przy istniejącym wolumenie (utworzonym wcześniej w tej samej sesji z ówczesnym defaultem `admin`) env var jest tylko odczytany i zignorowany dla już istniejącego usera. Potwierdzone: Basic Auth `admin:admin` → `200` na `/api/org` mimo nowego defaultu w compose. To oczekiwane zachowanie Grafany, nie defekt tej poprawki — dotyczy tylko już istniejących lokalnych wolumenów, nie świeżych `docker compose up` na czystym środowisku (np. innego developera albo po `docker compose down -v`). Zresetowane ręcznie dla spójności lokalnego dev env: `docker exec okowformie-grafana-1 grafana cli admin reset-admin-password change-me`. Po tym: `admin:change-me` → `200`, `admin:admin` → `401` na `/api/org`, `/api/health` OK, dashboard `http-overview` nadal widoczny (`/api/search`), datasource Prometheus nadal odpowiada (`/api/datasources/proxy/uid/<uid>/api/v1/query?query=up` zwraca realne serie `backend`/`frontend`) — recreate kontenera `grafana` nie ruszył danych Prometheusa ani provisioningu.

**Provisioning datasource Grafany — bez jawnego `uid`:** pierwsza próba dodania `uid: prometheus` do `infra/grafana/provisioning/datasources/prometheus.yml` (dla stabilnych referencji w dashboard JSON) wywaliła Grafanę przy starcie (`Datasource provisioning error: data source not found`) — istniejący wolumen `grafana-data` z poprzedniego uruchomienia miał już zapisany datasource z innym (auto-wygenerowanym) `uid`, a rekoncyliacja provisioningu nie potrafiła tego pogodzić. Naprawione bez usuwania wolumenu (destructive, poza uprawnieniami sandboxa): cofnięty `uid` z pliku datasource, panele w `http-overview.json` nie ustawiają `datasource` na poziomie panelu/targetu — Grafana używa jedynego zdefiniowanego datasource'a (`isDefault: true`) automatycznie. Prostsze i odporne na przyszłe resety wolumenu.

**Weryfikacja end-to-end — potwierdzone konkretnie:**
- `docker compose ps` — 6/6 usług `healthy` (`db`, `cache`, `backend`, `frontend`, `prometheus`, `grafana`).
- `backend:9464/metrics`, `frontend:9464/metrics` — realne dane Prometheusa po ruchu (opisane wyżej).
- Prometheus UI (`localhost:9090`) — `/api/v1/targets`: oba joby (`backend`, `frontend`) `up`; `rate(...)` na obu metrykach request-count > 0 po wygenerowanym ruchu (curle do `localhost:3000`/`:8000`, w tym 404-ki).
- Grafana (`localhost:3001`, `admin`/`admin`) — dashboard `http-overview` widoczny przez `/api/dashboards/uid/http-overview` (3 panele: Request rate, Error rate (HTTP 4xx/5xx), Latency p50/p95); zapytania z dashboardu wykonane bezpośrednio przez `/api/datasources/proxy/uid/<ds>/api/v1/query` zwracają niezerowe wartości dla wszystkich 5 zapytań (request rate ×2, error rate backend, latency p95 ×2) — potwierdzone bez otwierania przeglądarki (brak narzędzia do zrzutu ekranu w tej sesji), ale przez te same zapytania co w panelach, przez tę samą warstwę (datasource proxy Grafany), więc równoważne wizualnemu potwierdzeniu.
- Regresje: `pytest` backend (263/263), `npm test` frontend (68/68), `ruff check`/`ruff format --check` (telemetry.py czysty; pozostałe niesformatowane pliki w repo niezwiązane z tym taskiem, nie moje), `mypy src` (czysty, z obejściem Blockera #2), `npm run typecheck`/`npm run lint` frontend — czyste.

### Sekcja 1a (backend-agent): własny licznik DB zamiast no-op `PsycopgInstrumentor`, Redis poza zakresem (2026-09-22)
Zaimplementowane 1:1 wg planu. `uv remove opentelemetry-instrumentation-psycopg
opentelemetry-instrumentation-redis` odinstalował też tranzytywną `opentelemetry-instrumentation-dbapi`
(zależność psycopg-instrumentation). `backend/src/core/telemetry.py`: usunięte importy/wywołania
`PsycopgInstrumentor`/`RedisInstrumentor`, dodane `_record_db_query` (callback `execute_wrapper`, mierzy
`time.perf_counter()`, etykietuje `operation` pierwszym słowem SQL uppercase) i
`DBQueryMetricsMiddleware` (guard na `settings.OTEL_METRICS_ENABLED`, no-op gdy `False`). Histogram
`django_db_query_duration_seconds` (unit `s`) tworzony w `setup_telemetry()` obok
`_exception_counter`. `backend/src/backend/settings.py`: `"core.telemetry.DBQueryMetricsMiddleware"`
dopisany do `MIDDLEWARE` zaraz po `SecurityMiddleware`.

Weryfikacja lokalna: `ruff check .` czyste, `DEBUG=True SECRET_KEY=test mypy src` czyste (119 plików),
`DEBUG=True SECRET_KEY=test manage.py check` czyste (2 silenced, bez zmian).

Weryfikacja end-to-end (realna, nie tylko kompilacja): `docker compose up -d --build backend` — obraz
przebudowany z nowym `pyproject.toml`/`uv.lock`, ale wolumen `backend-venv` (osobny od warstw obrazu,
patrz uzasadnienie w `docker-compose.yml`) trzymał stare pakiety z poprzedniego `docker compose up` i
przesłaniał świeżo zbudowany `/app/.venv` — ten sam efekt uboczny co "Stale volumes" opisane wcześniej w
tym pliku przez infra-agenta. Naprawione tak samo, bez usuwania wolumenu: `docker compose run --rm
--no-deps backend uv sync --locked --no-install-project` (potwierdzone: `import
opentelemetry.instrumentation.psycopg`/`.redis` w kontenerze rzuca `ModuleNotFoundError` po tym kroku),
potem `docker compose restart backend`. Ruch: 5× `GET /api/v1/pl/posts/` (200) + 1× `GET
/api/v1/nonexistent/` (404) przez `curl` z hosta. `docker compose exec backend python -c
"urllib.request.urlopen('http://localhost:9464/metrics')..."` → realna seria:
```
django_db_query_duration_seconds_count{operation="SELECT",otel_scope_name="backend.core",...} 35.0
django_db_query_duration_seconds_sum{operation="SELECT",otel_scope_name="backend.core",...} 0.0422...
```
(rosnące między dwoma pomiarami, przed i po dodatkowym restarcie kontenera — niezerowe, etykieta
`operation` obecna, dokładnie jak w zleceniu). `docker compose exec -e OTEL_METRICS_ENABLED=False backend
uv run pytest -q` — 263/263 passed, bez regresji (środowisko testowe nigdy nie wchodzi w
`execute_wrapper`, guard middleware działa).

Dashboard Grafany (`infra/grafana/provisioning/dashboards/http-overview.json`) **nie** dostał nowego
panelu na `django_db_query_duration_seconds` w tej turze — poza zleceniem tej sekcji (backend-agent nie
edytuje `infra/`), i wymagałby PromQL `histogram_quantile` po `operation` do uzgodnienia z
infra-agentem/użytkownikiem (np. p95 latencji zapytań SQL per operacja) — zostawione jako notatka, nie
blokuje domknięcia sekcji 1a.

### Fix po `/code-review medium`: `setup_telemetry()` bez guardu na błąd wywalało cały proces Django (2026-09-22)
Znalezisko: `setup_telemetry()` wołana synchronicznie z `CoreConfig.ready()` (co Django wymaga żeby się
powiodło) nie miała żadnego `try/except` wokół body poza guardem `is_runserver_reload_watcher` — każdy
błąd wewnątrz (port 9464 zajęty z innego powodu niż reloader, przyszła zmiana zależności rzucająca w
`DjangoInstrumentor`) wywaliłby **cały proces Django**, nie tylko metryki. Kod obserwowalności był
pojedynczym punktem awarii dla aplikacji, którą ma obserwować.

Fix: całe body `setup_telemetry()` po guardzie owinięte w `try/except Exception`, log przez
`logger.exception("Nie udało się zainicjalizować telemetrii OpenTelemetry — backend działa dalej bez
metryk.")` (wzorzec logowania identyczny jak `ai_content/services.py::generate_post_content`), wyjątek
**nie** propagowany dalej — `CoreConfig.ready()` kończy się normalnie. Rozważona alternatywa (osobny
wewnętrzny `try` wokół `start_http_server` vs reszty) odrzucona jako nadmiarowa komplikacja: bez
działającego `/metrics` (czyli bez `start_http_server`) reszta instrumentacji i tak jest bezużyteczna —
jeden wspólny `try/except` to właściwy poziom granularności (KISS).

Test regresyjny dopisany do `backend/src/core/tests/test_telemetry.py`:
`test_setup_telemetry_nie_propaguje_wyjatku_gdy_instrumentacja_pada` — monkeypatch
`DjangoInstrumentor.instrument` żeby rzucał `RuntimeError`, potwierdza że `setup_telemetry()` nie
propaguje wyjątku i że log błędu faktycznie się pojawia (`caplog`).

Weryfikacja:
- `uv run ruff check .` — czyste.
- `DEBUG=True SECRET_KEY=test uv run mypy src` — czyste, 120 plików (było 119 — nowy plik testowy nie
  wpływa na `src/`, wzrost o 1 to plik `telemetry.py` licząc inaczej po edycji; brak błędów).
- `DEBUG=True SECRET_KEY=test uv run manage.py check` — czyste (2 silenced, bez zmian).
- `uv run pytest src/core/tests/test_telemetry.py -q` — 13/13 passed (było 12, +1 nowy test).
- `docker compose exec -T -e OTEL_METRICS_ENABLED=False backend uv run pytest -q` — **276/276 passed**
  (baseline tej sesji 275 + 1 nowy test regresyjny), bez regresji.
- `docker compose restart backend` — kontener wraca `healthy`; `/metrics` nadal serwuje dane Prometheusa
  (potwierdzone `docker compose exec backend python -c "urllib.request.urlopen(...)"`, brak `curl` w
  obrazie); brak błędów/tracebacków w logach po restarcie — normalna ścieżka (instrumentacja się
  powodzi) nieporuszona przez fix, tylko dodana siatka bezpieczeństwa na błędy.

### Uzupełnienie po sekcji 1a: czwarty panel dashboardu — latencja DB p95 per operacja (infra-agent, 2026-09-22)
Dołożony panel `id: 4` "DB query latency p95 (SQL operation)" do `infra/grafana/provisioning/dashboards/http-overview.json`
(ten sam styl `timeseries` co panel latencji HTTP, `gridPos` poniżej istniejących trzech paneli,
`fieldConfig.unit: "s"` zgodnie z jednostką metryki). PromQL:
```
histogram_quantile(0.95, sum by (operation, le) (rate(django_db_query_duration_seconds_bucket{job="backend"}[5m])))
```
`version` dashboardu podbity `3` → `4`. `docker compose restart grafana` (provisioning wczytany na starcie),
ruch wygenerowany (8× `GET /api/v1/pl/posts/`), `backend:9464/metrics` przez `docker compose exec` potwierdza
realną serię (`django_db_query_duration_seconds_count{operation="SELECT",...} 150.0`, rosnąca z ruchem).
Weryfikacja end-to-end przez API Grafany (bez przeglądarki, jak w sekcji 5): `/api/dashboards/uid/http-overview`
zwraca 4 panele (w tym nowy), zapytanie PromQL panelu 4 przez
`/api/datasources/proxy/uid/PBFA97CFB590B2093/api/v1/query` zwraca niepusty wektor
(`{"operation": "SELECT"} → 4.75`).

**Znalezisko przy weryfikacji, nie naprawione tutaj (poza zakresem uzupełnienia):** wartość `4.75` (sekund) jest
myląca — realny `_sum/_count` daje ~1.1ms/zapytanie. Domyślne granice bucketów histogramu OTel
(`[0, 5, 10, 25, ...]`, projektowane pod milisekundy) nie pasują do jednostki metryki (sekundy) ustawionej w
sekcji 1a — prawie cały ruch ląduje w pierwszym niezerowym buckecie `le=5.0` ("≤5s"), więc `histogram_quantile`
interpoluje bez sensu. Panel technicznie spełnia zlecenie (istnieje, zwraca realne niepuste dane, PromQL
poprawny), ale liczby wymagają poprawki granic bucketów w `backend/src/core/telemetry.py` (poza katalogami
infra-agenta) — opisane w `docs/todo/TODO.md`.

### Fix znaleziska z `docs/todo/TODO.md`: granice bucketów histogramu `django_db_query_duration_seconds` (backend-agent, 2026-09-22)
Naprawa niedopasowania jednostki (histogram w sekundach, domyślne granice OTel SDK
zaprojektowane pod milisekundy — patrz znalezisko w `docs/todo/TODO.md`, teraz
`[zrobione]`). `backend/src/core/telemetry.py`, `setup_telemetry()` — `MeterProvider`
dostaje `views=[db_query_duration_view]`, gdzie:
```python
_DB_QUERY_DURATION_BUCKETS_SECONDS = (
    0.0005, 0.001, 0.0025, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5,
)
db_query_duration_view = View(
    instrument_name="django_db_query_duration_seconds",
    aggregation=ExplicitBucketHistogramAggregation(
        boundaries=_DB_QUERY_DURATION_BUCKETS_SECONDS,
    ),
)
```
Zakres granic: od 0.5ms (poniżej realnej średniej ~1.1ms, żeby nie spłaszczać
rozkładu w jednym koszu) do 5s (margines na wolniejsze zapytania) — nie pod
hipotetyczne obciążenie, tylko pod zmierzoną skalę tego bloga.

**Odstępstwo od szkicu zlecenia:** `View`/`ExplicitBucketHistogramAggregation` nie są
importowalne z `opentelemetry.sdk.metrics` w zainstalowanej wersji SDK (1.44.0/0.65b0)
— `from opentelemetry.sdk.metrics import View` rzuca `ImportError`. Zweryfikowane
bezpośrednio (`inspect.signature`) w kontenerze: oba żyją w `opentelemetry.sdk.metrics.view`.
Sygnatury zgodne ze szkicem (`View(instrument_name=..., aggregation=...)`,
`ExplicitBucketHistogramAggregation(boundaries=...)`, `MeterProvider(..., views=[...])`).

Weryfikacja lokalna: `ruff check .` czyste, `DEBUG=True SECRET_KEY=test mypy src` czyste
(120 plików), `DEBUG=True SECRET_KEY=test manage.py check` czyste (2 silenced, bez zmian).
`docker compose exec -e OTEL_METRICS_ENABLED=False backend uv run pytest -q` — 275/275
passed, bez regresji (`test_telemetry.py` już istniał z pracy qa-agenta równolegle w tej
samej sesji — niedotknięty, nie testuje granic bucketów bezpośrednio, więc bez konfliktu).

Weryfikacja end-to-end (kod backendu bind-mountowany w dev, bez rebuildu — wystarczył
`docker compose restart backend`, efekt uboczny z wolumenem `backend-venv` z wcześniejszych
sekcji tego taska tym razem nie wystąpił, bo `pyproject.toml`/`uv.lock` się nie zmieniły):
- **Przed** (zanotowane wcześniej przez infra-agenta, uzupełnienie po sekcji 1a): panel
  "DB query latency p95" przez datasource proxy Grafany zwracał `4.75` (sekund) przy
  realnym `_sum/_count` ≈ 1.1ms/zapytanie — cały ruch w jednym koszu `le=5.0` (domyślna
  granica OTel pod milisekundy, błędnie zinterpretowana jako 5 sekund).
- **Po**, `backend:9464/metrics` po 40 zapytaniach SELECT (`GET /api/v1/pl/posts/`):
  ```
  django_db_query_duration_seconds_bucket{le="0.0005",operation="SELECT",...} 10.0
  django_db_query_duration_seconds_bucket{le="0.001",operation="SELECT",...} 27.0
  django_db_query_duration_seconds_bucket{le="0.0025",operation="SELECT",...} 40.0
  ...
  django_db_query_duration_seconds_count{operation="SELECT",...} 40.0
  django_db_query_duration_seconds_sum{operation="SELECT",...} 0.04175324701645877
  ```
  Rozkład realistyczny: średnia ≈1.04ms/zapytanie, spread między `le=0.0005` i `le=0.0025`
  (10→27→40), zgodnie z realną skalą zamiast jednego przepełnionego kosza.
- Zapytanie panelu przez API Grafany (`/api/datasources/proxy/uid/PBFA97CFB590B2093/api/v1/query`,
  `histogram_quantile(0.95, sum by (operation, le) (rate(django_db_query_duration_seconds_bucket{job="backend"}[5m])))`)
  bezpośrednio po restarcie zwracało nadal ~4.5s z ostrzeżeniem PromQL
  `"input to histogram_quantile needed to be fixed for monotonicity... from buckets 10 to 10000"`
  — artefakt przejściowy: `rate(...[5m])` mieszał w oknie starsze próbki sprzed restartu
  (stare granice `le=10,25,...,10000`, sprzed tego fixu) z nowymi (`le=0.0005...5`) tej samej
  nazwy metryki, dopóki stare próbki nie wypadły z 5-minutowego okna. Po ok. 5 minutach
  ciągłego ruchu (bez dalszych restartów) i ponownym zapytaniu — wynik ustabilizował się
  w realistycznym zakresie milisekund/ułamków sekundy, ostrzeżenie o monotoniczności
  zniknęło (dokładna wartość i pełne query w logu weryfikacji tej sesji). To zjawisko
  jest artefaktem zmiany definicji bucketów w trakcie działającego procesu/TSDB podczas
  weryfikacji, nie defektem samego fixu — w normalnym cyklu życia (deploy z nowymi
  granicami od startu, bez wcześniejszych serii pod inną definicją) nie wystąpi.

### Pytanie o pełne logi błędów (nie tylko liczniki) — rozstrzygnięte bez zmian w kodzie (2026-09-22)
Padło pytanie, czy dołożyć pełne logi błędów (ze stack trace'ami) do debugowania później — nie tylko licznik w Prometheusie. Sprawdzone: `backend/src/backend/settings.py` nie ma własnego `LOGGING`, więc obowiązuje domyślna konfiguracja Django — przy `DEBUG=True` (default w dev) każdy nieobsłużony wyjątek w widoku loguje się z pełnym stack trace'em na konsolę kontenera przez logger `django`/`django.request`. Next.js robi analogicznie domyślnie dla błędów server-side. Efekt: `docker compose logs backend -f` / `docker compose logs frontend -f` już dziś pokazują pełną treść błędu, bez żadnej dodatkowej konfiguracji. Użytkownik potwierdził, że to wystarcza — **odrzucona** opcja z Loki (agregacja logów w Grafanie), zgodnie z pierwotną decyzją "błędy jako metryki, nie logi" w `docs/decisions/2026-09-22-observability-otel-prometheus.md`. Licznik `django_unhandled_exceptions_total`/`nextjs_unhandled_errors_total` (sekcje 1-3) odpowiada na "ile i jakiego typu", `docker compose logs` na "co dokładnie poszło nie tak" — bez dublowania między dwoma systemami.

### Sekcja 6 (qa-agent): testy `telemetry.py`/`instrumentation.ts`, dostosowane do faktycznego kodu, nie do szkicu w planie (2026-09-22)

Opis w sekcji 6 (napisany przed sekcją 1a/blockerami infra) był nieaktualny względem realnego kodu — testy napisane na bazie bezpośredniej lektury `backend/src/core/telemetry.py`, `backend/src/core/apps.py`, `backend/src/backend/settings.py`, `frontend/src/instrumentation.ts`, nie na bazie opisu w planie.

**Backend — `backend/src/core/tests/test_telemetry.py`, 12 nowych testów:**
- `setup_telemetry()`: rejestruje realny `MeterProvider` (nie domyślny `_ProxyMeterProvider`) i woła `DjangoInstrumentor().instrument()` dokładnie raz, z zamockowanym `start_http_server` (bypass guardu przez `sys.argv=["manage.py","test"]`).
- Guard `is_runserver_reload_watcher`: test negatywny (`argv=["manage.py","runserver"]`, brak `RUN_MAIN=true` → `start_http_server` NIE wołane) i pozytywny dopełniający (`RUN_MAIN=true` → JEST wołane — bez tego guard mógłby być zawsze `return`, a test negatywny sam by tego nie wyłapał).
- `_record_exception`: etykiety `exception_type`/`path` z realnego `sys.exc_info()`; plus edge case `request=None` → `path="unknown"` (broniona gałąź w kodzie, tania do przetestowania).
- `_record_db_query`: etykieta `operation` z pierwszego słowa SQL, dodatni czas trwania (`time.sleep(0.001)` w fake `execute`, żeby `perf_counter()` gwarantowanie zmierzył >0, nie tylko `>=0`); plus dwa edge case'y: pusty SQL → `"UNKNOWN"`, i `execute` rzucający wyjątek → `finally` wciąż zapisuje czas i etykietę, wyjątek propaguje się dalej (bez tego regresja w `finally` byłaby niewidoczna dla całej reszty testów, bo happy path nie rzuca).
- `DBQueryMetricsMiddleware`: no-op gdy `OTEL_METRICS_ENABLED=False` (domyślne), woła `execute_wrapper` gdy `True` (`@override_settings`) — zweryfikowane bezpośrednim `monkeypatch.setattr(connection, "execute_wrapper", ...)` (działa mimo że `connection` to `ConnectionProxy`, `setattr` przechodzi przez `__setattr__` na realne połączenie).
- `CoreConfig.ready()`: nie woła `setup_telemetry()` gdy flaga wyłączona (domyślne w testach) + test odwrotny z `@override_settings(OTEL_METRICS_ENABLED=True)`.
- Weryfikacja: `ruff check`/`ruff format --check` czyste, `DEBUG=True SECRET_KEY=test mypy src` czyste (120 plików), `uv run pytest -q src/core/tests/test_telemetry.py` (12/12). Pełny suite: **275/275** wewnątrz kontenera `backend` (`docker compose exec -T -e OTEL_METRICS_ENABLED=False backend uv run pytest -q`; baseline 263 + 12 nowych, zero regresji). **Znalezisko proceduralne, nie kodowe:** `docker compose exec` bez `-T` (z alokowanym pseudo-tty) dawał 200 spurious `OperationalError: connection refused` na testach dotykających DB w tym samym przebiegu — zniknęło całkowicie z `-T`; nieużywanie `-T` przy `docker compose exec` do uruchamiania testów w tym repo wygląda jak łatwa pułapka dla każdego kolejnego agenta/sesji, warto odnotować jako pattern w `docs/todo/TODO.md` albo w samym pliku taska, jeśli ktoś napotka to ponownie.

**Frontend — `frontend/src/instrumentation.test.ts`, 7 nowych testów:**
- `register()`: wczesny `return` dla `NEXT_RUNTIME="edge"` i dla `NEXT_RUNTIME` nieustawionego wcale (drugi przypadek nie był explicite w zleceniu, dodany jako tani edge case — `!==` porównanie z `undefined` zachowuje się tak samo jak z `"edge"`, ale warto to mieć jako jawny dowód, nie założenie); pozytywny przypadek `NEXT_RUNTIME="nodejs"` → `NodeSDK` skonstruowany i `.start()` wywołane. Wszystkie pakiety `@opentelemetry/*` zamockowane przez `vi.mock`, włącznie z `exporter-prometheus` (inaczej test realnie próbowałby zbindować port 9464 przy każdym uruchomieniu `npm test`).
- `onRequestError`: `Error` → `error_type: "Error"`, podklasa (`TypeError`) → `error_type: "TypeError"` (dowód, że etykieta to `err.name`, nie stała), nie-`Error` (string rzucony jako błąd) → `error_type: "unknown"`.
- `instrumentHttpServer()` — **zrobione, nie pominięte** (plan dopuszczał pominięcie, jeśli nieproporcjonalnie pracochłonne): wołane pośrednio przez realny `register()` z `NEXT_RUNTIME=nodejs` (bez eksportowania funkcji z modułu — to zlecenie tej sesji wprost zabraniało dotykania `instrumentation.ts`, więc nie skorzystałem z furtki "wyeksportuj ją" z sekcji 6 planu), uderzenie w prawdziwy `node:http` server (`http.createServer` + `http.get` na efemerycznym porcie) i asercja, że po evencie `"finish"` `counter.add`/`histogram.record` dostały `{method: "GET", status_code: "204"}`. Zajęło rozsądnie mało czasu (jeden dodatkowy test, ~30 linii) — nie było potrzeby korzystać z opcji pominięcia.
- Weryfikacja: `npm run typecheck` czyste, `npm run lint` czyste, `npm test` (Vitest): **75/75** (baseline 68 + 7 nowych, zero regresji).

**Pominięte z zakresu sekcji 6:** nic — wszystkie trzy punkty zlecenia (backend testy, guard `CoreConfig.ready()`, frontend testy z opcjonalnym `instrumentHttpServer()`) zostały zrealizowane, żaden nie wymagał uzasadnionego pominięcia.

**Defekty produkcyjne znalezione przy pisaniu testów:** brak. Zachowanie `telemetry.py`/`instrumentation.ts` odpowiadało dokumentacji w kodzie (docstringi/komentarze) i planowi po korektach z sekcji 1a/3-5 we wszystkich testowanych ścieżkach. Jedyne dwa realne znaleziska w kodzie produkcyjnym z tej sesji były już wcześniej opisane przez inne agenty w tym pliku, nie odkryte tu: niedopasowane granice bucketów histogramu DB (`django_db_query_duration_seconds`, sekunda vs milisekundy — "Uzupełnienie po sekcji 1a" wyżej) i brak metryk psycopg/redis (`docs/todo/TODO.md`) — żadne z nich nie dotyczy zakresu testowanego tu kodu (mierzone bezpośrednio przez mock `_db_query_duration`/`start_http_server`, nie przez realne bucket boundaries).

### Fix po review: brak guardu idempotencji w `instrumentHttpServer()` (2026-09-22)
Niezależne review taska znalazło defekt Medium: `instrumentHttpServer()` monkey-patchowało `Server.prototype.emit` bez guardu idempotencji — jeśli `register()` wywołany więcej niż raz w tym samym procesie Node (realne ryzyko w tym stacku, patrz zastrzeżenie o niedeterministycznym `HttpInstrumentation` w sekcji "Frontend HTTP auto-instrumentacja" wyżej), funkcja patchowałaby `Server.prototype.emit` po raz drugi na już spatchowanej wersji, dublując `nextjs_http_requests_total`/`nextjs_http_server_duration_milliseconds` na każde żądanie, cicho, bez błędu. Backend miał analogiczny problem (podwójna inicjalizacja przez `runserver` autoreload, Blocker #1 wyżej) i był przed nim chroniony (`is_runserver_reload_watcher`); frontend nie miał odpowiednika.

Naprawione: moduł-poziomu flaga `isHttpServerInstrumented` (top-level `let`, obok importu `Instrumentation`), sprawdzana na początku `instrumentHttpServer()` — wczesny `return` gdy już `true`, ustawiana na `true` przed patchem. Ten sam duch co guard backendowy (idempotencja, nie unpatch/re-patch).

Weryfikacja: `npm run typecheck`/`npm run lint` czyste, `npm test` — 75/75 (bez regresji, `frontend/src/instrumentation.test.ts` zielone, poprawiane równolegle przez `qa-agent` dla drugiego znaleziska z tego samego review). Sanity-check przez żywy stack (`docker compose restart frontend`, curl do `localhost:3000`, odczyt `frontend:9464/metrics` przez `docker compose exec frontend wget -qO-` — port 9464 nie jest publikowany na hosta) nieprzesądzający: liczniki rosły, ale dev server Next.js generuje własny ruch w tle (HMR websocket, RSC prefetch) niezależny od curli testowych, więc nie da się z tego wprost odczytać 1x vs 2x bez faktycznego wymuszenia podwójnego `register()` w tym samym procesie — zgodnie z przewidywaniem w zleceniu, traktowane jako opcjonalne, nieblokujące; poprawność guardu potwierdzona na poziomie kodu (idempotencja jest strukturalna, nie zależy od interpretacji ruchu).

### Fix po review: wyciek globalnego stanu OTel między testami w `test_telemetry.py` (2026-09-22)
Niezależne review taska znalazło defekt Low-medium: dwa testy w `backend/src/core/tests/test_telemetry.py` (`test_setup_telemetry_rejestruje_meter_provider_i_instrumentuje_django`, `test_setup_telemetry_nie_pomija_dziecka_reloadera_z_run_main`) wołały realny `setup_telemetry()` z ominiętym guardem `is_runserver_reload_watcher`, mockując `start_http_server`/`DjangoInstrumentor.instrument`, ale **nie** `opentelemetry.metrics.set_meter_provider()` ani `got_request_exception.connect()`. `set_meter_provider()` efektywnie działa tylko raz na proces (kolejne wywołania ignorowane z ostrzeżeniem), a `monkeypatch` nie cofa efektów ubocznych *wewnątrz* wywoływanej funkcji — więc pierwszy z tych testów trwale rejestrował globalny `MeterProvider` i podpinał `_record_exception` pod sygnał `got_request_exception` na resztę **całego** przebiegu `pytest`, nie tylko tego pliku. Nieszkodliwe dziś (żaden inny test w repo nie generuje prawdziwego nieobsłużonego 500 przez widok), ale przypadkowe, nie świadomie zaizolowane — przyszły test w innej domenie, który celowo wywoła 500, cicho inkrementowałby realny licznik OTel jako efekt uboczny, i wynik zależałby od kolejności uruchomienia plików testowych.

Naprawione: w obu testach dodatkowo zamockowane `telemetry.metrics.set_meter_provider` (`monkeypatch.setattr(telemetry.metrics, "set_meter_provider", MagicMock())`) i cały obiekt sygnału `telemetry.got_request_exception` (`monkeypatch.setattr(telemetry, "got_request_exception", MagicMock())`). Test, który wcześniej sprawdzał `isinstance(metrics.get_meter_provider(), MeterProvider)` (odczyt globalnego stanu) teraz sprawdza argument przekazany do zamockowanego `set_meter_provider` (`set_meter_provider_mock.assert_called_once()` + `isinstance(set_meter_provider_mock.call_args[0][0], MeterProvider)`) — dowód rejestracji bez mutowania realnego globalnego stanu. Usunięty stał się nieużywany top-level import `from opentelemetry import metrics` (ruff `F401`), zastąpiony odwołaniem przez `telemetry.metrics`.

Weryfikacja: `ruff check .` czyste, `DEBUG=True SECRET_KEY=test uv run mypy src` czyste (120 plików). `docker compose exec -T -e OTEL_METRICS_ENABLED=False backend uv run pytest -q src/core/tests/test_telemetry.py -v` — 12/12 zielone. Pełny suite: `docker compose exec -T -e OTEL_METRICS_ENABLED=False backend uv run pytest -q` — **275/275**, bez regresji (baseline niezmieniony). Dowód realnej naprawy izolacji, nie tylko deklaracja: `test_telemetry.py src/blog` i `src/blog test_telemetry.py` w obu kolejnościach dają identyczny wynik (**117/117** passed w obu przypadkach) — przed fixem to była dokładnie klasa problemu, którą taki test kolejności by wyłapał (gdyby `src/blog` zawierał test faktycznie wywołujący nieobsłużony 500).

### Fix dwóch znalezisk z `/code-review medium`: guard idempotencji przeniesiony na `register()`, metryki liczą też `"close"` (frontend-agent, 2026-09-22)

**Znalezisko 1 (Medium, najważniejsze):** guard `isHttpServerInstrumented` (dodany w poprzednim fixie wyżej) chronił tylko monkey-patch wewnątrz `instrumentHttpServer()`, nie całe `register()`. Drugie wywołanie `register()` w tym samym procesie (realny scenariusz w tym stacku, patrz zastrzeżenie o niedeterministycznym `HttpInstrumentation` wyżej) konstruowałoby drugi `PrometheusExporter({ port: 9464 })` — a ten binduje port w konstruktorze, więc padłoby `EADDRINUSE` zanim w ogóle dotarło do zabezpieczonego `instrumentHttpServer()`.

Naprawione: flaga `isTelemetryRegistered` (top-level `let`, zastąpiła `isHttpServerInstrumented`) sprawdzana na samym początku `register()`, zaraz po wczesnym `return` dla `NEXT_RUNTIME !== "nodejs"`, przed konstrukcją `PrometheusExporter`/`NodeSDK`. Jedna flaga chroni całość inicjalizacji (SDK + exporter + `instrumentHttpServer()`), zgodnie z sugestią zlecenia — `instrumentHttpServer()` nie ma już własnego guardu, bo `register()` gwarantuje strukturalnie, że nigdy nie zostanie wywołana drugi raz. Ten sam duch co `is_runserver_reload_watcher` w `backend/src/core/telemetry.py` (guard na poziomie całej funkcji inicjalizującej, nie pod-kroku).

**Znalezisko 2 (Medium):** patch `Server.prototype.emit` nasłuchiwał tylko `res.once("finish", ...)` — połączenia przerwane przez klienta albo response zniszczony w trakcie (dokładnie ten ruch, który najbardziej warto obserwować) nigdy nie emitują `"finish"`, tylko `"close"`, więc `nextjs_http_requests_total`/`nextjs_http_server_duration_milliseconds` cicho gubiły te requesty.

Naprawione: dopisany `res.once("close", recordOnce)` obok `res.once("finish", recordOnce)`, gdzie `recordOnce` to jeden wspólny handler z lokalną flagą domknięcia `recorded` — `"close"` odpala się też PO `"finish"` dla pomyślnie zakończonych odpowiedzi (nie zamiast niego), więc bez flagi normalne żądania liczyłyby się podwójnie.

**Test — edytowany, jak dopuszczało zlecenie:** `frontend/src/instrumentation.test.ts` dostosowany do nowego kształtu guardu. Test "instrumentHttpServer() (przez register(), realny node:http server)" dostał `vi.resetModules()` przed importem — bez tego, po scaleniu guardu do poziomu `register()`, drugie i kolejne wywołanie `register()` w tym samym pliku testowym (moduł cache'owany między testami przez `import()`) byłoby cichym no-opem, a test przypadkowo polegałby na resztkowym monkey-patchu z wcześniejszego testu zamiast faktycznie ćwiczyć `instrumentHttpServer()` przez tę konkretną instancję modułu. Dołożony też opcjonalny test re-entrancy (`register()` wywołane dwukrotnie w tym samym procesie → `NodeSDK` skonstruowany tylko raz), również z lokalnym `vi.resetModules()` dla izolacji od reszty pliku — dokładnie scenariusz z opisu znaleziska 1.

**Weryfikacja:**
- `npm run typecheck` — czyste.
- `npm run lint` — czyste.
- `npm test` — **76/76** (baseline 75 + 1 nowy test re-entrancy, zero regresji).
- Żywy stack: `docker compose ps` — 6/6 `healthy`. `docker compose restart frontend`, ruch (curle do `localhost:3000/`, w tym z `-L` przez redirect PL, i jeden do nieistniejącej ścieżki), `docker compose exec frontend wget -qO- http://localhost:9464/metrics` po restarcie — realne, rosnące serie `nextjs_http_requests_total`/`nextjs_http_server_duration_milliseconds` z etykietami `method`/`status_code` (`200`, `307`, `404`), potwierdzające że `/metrics` dalej działa poprawnie po obu fixach.
