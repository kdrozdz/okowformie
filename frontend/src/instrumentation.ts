/**
 * Next.js instrumentation hook (stabilny w Next 16 — bez
 * `experimental.instrumentationHook`). `register()` woła się raz przy
 * starcie procesu serwera, w każdym dostępnym runtime; `onRequestError`
 * woła się na każdy nieobsłużony błąd złapany przez error-boundary
 * Next.js (Server Components, Route Handlers, Server Actions).
 *
 * Eksponuje metryki HTTP i licznik błędów w formacie Prometheusa na
 * porcie 9464 — patrz `docs/decisions/2026-09-22-observability-otel-prometheus.md`.
 */
import type { Instrumentation } from "next";

// Guard idempotencji dla całej inicjalizacji telemetrii (SDK + exporter +
// `instrumentHttpServer()`) — analogiczny w duchu do
// `is_runserver_reload_watcher` w `backend/src/core/telemetry.py`. `register()`
// może zostać wywołane więcej niż raz w tym samym procesie Node (patrz
// komentarz o niedeterministycznym `HttpInstrumentation` niżej). Musi chronić
// `register()` w całości, nie tylko `instrumentHttpServer()`: `PrometheusExporter`
// binduje port 9464 w swoim konstruktorze, więc drugie wywołanie `register()`
// padłoby `EADDRINUSE` zanim w ogóle dotarłoby do monkey-patchu `Server.prototype.emit`.
let isTelemetryRegistered = false;

export async function register(): Promise<void> {
  // Instrumentacja OTel jest specyficzna dla Node.js (server HTTP,
  // eksporter Prometheusa) — Edge Runtime i klient nie mają czego tu
  // robić. Wczesny return + dynamiczne importy poniżej (zamiast
  // statycznych na górze pliku) trzymają te ciężkie zależności poza
  // bundlem Edge/klienta, mimo że ten plik jest analizowany przez
  // bundler dla każdego runtime.
  if (process.env.NEXT_RUNTIME !== "nodejs") {
    return;
  }
  if (isTelemetryRegistered) {
    return;
  }
  isTelemetryRegistered = true;

  const { NodeSDK } = await import("@opentelemetry/sdk-node");
  const { PrometheusExporter } = await import("@opentelemetry/exporter-prometheus");
  const { resourceFromAttributes } = await import("@opentelemetry/resources");
  const { ATTR_SERVICE_NAME } = await import("@opentelemetry/semantic-conventions");

  // Serwer Prometheusa wbudowany w PrometheusExporter — nie potrzeba
  // OTel Collectora (decyzja `docs/decisions/2026-09-22-observability-otel-prometheus.md`).
  const exporter = new PrometheusExporter({ port: 9464 });

  const sdk = new NodeSDK({
    resource: resourceFromAttributes({
      [ATTR_SERVICE_NAME]: "frontend",
    }),
    metricReaders: [exporter],
    // Bez `@opentelemetry/instrumentation-http` — zweryfikowane empirycznie
    // (task 14, sekcja 5), że w tym stacku (Next.js 16 + Turbopack dev
    // server) jego metryki HTTP serwera są niedeterministyczne: ten sam
    // kod, ten sam ruch, czasem zapisuje dane, czasem zwraca
    // "no registered metrics" (prawdopodobnie zdublowany stan singletona
    // `@opentelemetry/api` między chunkami bundlowanymi osobno przez
    // Turbopack dla dynamicznych importów). Zamiast na to liczyć,
    // `instrumentHttpServer()` niżej liczy request/duration ręcznie przez
    // to samo źródło prawdy (`http.Server` — faktyczny serwer, na którym
    // stoi `next dev`/`next start`, potwierdzone empirycznie), deterministycznie.
  });

  sdk.start();
  await instrumentHttpServer();
}

/**
 * Ręczny licznik żądań HTTP i histogram czasu trwania, wpięty w
 * `http.Server.prototype.emit("request", ...)` — fallback opisany w planie
 * taska 14 (sekcja 5) na wypadek, gdyby auto-instrumentacja OTel
 * (`HttpInstrumentation`) nie emitowała metryk niezawodnie; patrz komentarz
 * w `register()` dla pełnego uzasadnienia.
 *
 * Bez własnego guardu idempotencji — `register()` gwarantuje (przez
 * `isTelemetryRegistered`), że ta funkcja nigdy nie zostanie wywołana więcej
 * niż raz na proces.
 */
async function instrumentHttpServer(): Promise<void> {
  const { metrics } = await import("@opentelemetry/api");
  const { Server } = await import("node:http");

  const meter = metrics.getMeter("frontend.core");
  const requestCounter = meter.createCounter("nextjs_http_requests_total", {
    description: "Liczba żądań HTTP obsłużonych przez serwer Next.js.",
  });
  const durationHistogram = meter.createHistogram("nextjs_http_server_duration_milliseconds", {
    description: "Czas trwania żądań HTTP obsłużonych przez serwer Next.js.",
    unit: "ms",
  });

  const originalEmit = Server.prototype.emit;
  // `Server.prototype.emit` ma typ `(event: string | symbol, ...args: any[]) => boolean`
  // w `@types/node` (sygnatura `EventEmitter.emit`) — nie da się jej zawęzić
  // bez `any` na granicy z wbudowanym typem Node, stąd jawne opt-outy niżej
  // zamiast cichego dopasowania.
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  Server.prototype.emit = function (this: unknown, event: string | symbol, ...args: any[]): boolean {
    if (event === "request") {
      const [req, res] = args as [
        import("node:http").IncomingMessage,
        import("node:http").ServerResponse,
      ];
      const startedAt = performance.now();
      // Połączenie przerwane przez klienta (albo response zniszczony w
      // trakcie — dokładnie ten ruch, który najbardziej warto obserwować)
      // nigdy nie emituje `"finish"`, tylko `"close"` — sam nasłuch na
      // `"finish"` cicho gubiłby te requesty. Ale `"close"` odpala się też
      // PO `"finish"` dla pomyślnie zakończonych odpowiedzi (nie zamiast
      // niego), więc bez flagi `recorded` normalne żądania liczyłyby się
      // podwójnie.
      let recorded = false;
      const recordOnce = () => {
        if (recorded) {
          return;
        }
        recorded = true;
        const labels = {
          method: req.method ?? "unknown",
          status_code: String(res.statusCode),
        };
        requestCounter.add(1, labels);
        durationHistogram.record(performance.now() - startedAt, labels);
      };
      res.once("finish", recordOnce);
      res.once("close", recordOnce);
    }
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    return (originalEmit as any).apply(this, [event, ...args]);
  };
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
