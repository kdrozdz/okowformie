/**
 * `instrumentation.ts` — task 14 (`docs/decisions/2026-09-22-observability-otel-prometheus.md`).
 *
 * Wszystkie pakiety OTel są mockowane (`vi.mock`), włącznie z
 * `@opentelemetry/exporter-prometheus` — bez tego `register()` faktycznie
 * próbowałby zbindować port 9464 w każdym uruchomieniu testów (ten sam
 * problem co `start_http_server` po stronie backendu, patrz
 * `backend/src/core/tests/test_telemetry.py`).
 *
 * `instrumentHttpServer()` nie jest eksportowana z `instrumentation.ts`
 * (zlecenie tego taska wprost zabrania dotykania kodu produkcyjnego) — testowana
 * pośrednio, wołając prawdziwe `register()` (z NEXT_RUNTIME=nodejs) i
 * uderzając w realny `node:http` server, zamiast wywoływać ją bezpośrednio.
 */
import http from "node:http";

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const nodeSdkConstructor = vi.fn();
const nodeSdkStart = vi.fn();

vi.mock("@opentelemetry/sdk-node", () => ({
  NodeSDK: class {
    constructor(...args: unknown[]) {
      nodeSdkConstructor(...args);
    }
    start() {
      nodeSdkStart();
    }
  },
}));

// Mockowany, żeby test nie próbował realnie zbindować portu 9464
// (`PrometheusExporter` startuje własny serwer HTTP w konstruktorze).
vi.mock("@opentelemetry/exporter-prometheus", () => ({
  PrometheusExporter: class {},
}));

vi.mock("@opentelemetry/resources", () => ({
  resourceFromAttributes: vi.fn((attrs: Record<string, unknown>) => attrs),
}));

vi.mock("@opentelemetry/semantic-conventions", () => ({
  ATTR_SERVICE_NAME: "service.name",
}));

const counterAdd = vi.fn();
const histogramRecord = vi.fn();
const createCounter = vi.fn(() => ({ add: counterAdd }));
const createHistogram = vi.fn(() => ({ record: histogramRecord }));
const getMeter = vi.fn(() => ({ createCounter, createHistogram }));

vi.mock("@opentelemetry/api", () => ({
  metrics: { getMeter },
}));

describe("instrumentation.ts", () => {
  const originalNextRuntime = process.env.NEXT_RUNTIME;

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    if (originalNextRuntime === undefined) {
      delete process.env.NEXT_RUNTIME;
    } else {
      process.env.NEXT_RUNTIME = originalNextRuntime;
    }
  });

  describe("register()", () => {
    it("wczesny return dla NEXT_RUNTIME !== 'nodejs' — SDK nie jest inicjalizowany", async () => {
      process.env.NEXT_RUNTIME = "edge";
      const { register } = await import("./instrumentation");

      await register();

      expect(nodeSdkConstructor).not.toHaveBeenCalled();
      expect(nodeSdkStart).not.toHaveBeenCalled();
    });

    it("bez NEXT_RUNTIME ustawionego w ogóle — również wczesny return", async () => {
      delete process.env.NEXT_RUNTIME;
      const { register } = await import("./instrumentation");

      await register();

      expect(nodeSdkConstructor).not.toHaveBeenCalled();
    });

    it("NEXT_RUNTIME === 'nodejs' — inicjalizuje NodeSDK i woła start()", async () => {
      process.env.NEXT_RUNTIME = "nodejs";
      const { register } = await import("./instrumentation");

      await register();

      expect(nodeSdkConstructor).toHaveBeenCalledOnce();
      expect(nodeSdkStart).toHaveBeenCalledOnce();
    });
  });

  describe("instrumentHttpServer() (przez register(), realny node:http server)", () => {
    it("liczy realne żądanie HTTP — counter.add i histogram.record z etykietami method/status_code", async () => {
      // `vi.resetModules()` — bez tego, guard idempotencji `isTelemetryRegistered`
      // (moduł-poziomu, przetrwałby dzięki cache'owaniu modułu przez `import()`
      // między testami tego pliku) sprawiłby, że `register()` niżej byłby
      // cichym no-opem, jeśli jakiś wcześniejszy test w tym pliku już wywołał
      // `register()` z powodzeniem — test przypadkowo polegałby wtedy na
      // resztkowym monkey-patchu `Server.prototype.emit` z innego testu,
      // zamiast faktycznie ćwiczyć `instrumentHttpServer()` przez to
      // wywołanie `register()`.
      vi.resetModules();
      process.env.NEXT_RUNTIME = "nodejs";
      const { register } = await import("./instrumentation");
      await register();

      const server = http.createServer((_req, res) => {
        res.statusCode = 204;
        res.end();
      });

      await new Promise<void>((resolve) => server.listen(0, resolve));
      const address = server.address();
      if (address === null || typeof address === "string") {
        throw new Error("Nie udało się ustalić portu testowego serwera HTTP.");
      }

      await new Promise<void>((resolve, reject) => {
        http
          .get(`http://127.0.0.1:${address.port}/`, (res) => {
            res.resume();
            res.on("end", resolve);
          })
          .on("error", reject);
      });

      // `res.end()` kończy odpowiedź natychmiast, ale event `"finish"`
      // (na którym wisi zapis metryki, patrz `instrumentHttpServer` w
      // `instrumentation.ts`) leci w kolejnej iteracji event loopa — bez
      // tego mikro-czekania asercja poniżej łapałaby wyścig.
      await new Promise((resolve) => setImmediate(resolve));

      server.close();

      expect(counterAdd).toHaveBeenCalledWith(1, { method: "GET", status_code: "204" });
      expect(histogramRecord).toHaveBeenCalledWith(expect.any(Number), {
        method: "GET",
        status_code: "204",
      });
    });
  });

  describe("register() — re-entrancy", () => {
    it("wywołane dwukrotnie w tym samym procesie — NodeSDK inicjalizowany tylko raz", async () => {
      // `vi.resetModules()` lokalnie w tym teście: guard `isTelemetryRegistered`
      // jest stanem modułowym, który przetrwałby między testami dzięki
      // cache'owaniu modułu przez `import()` — świeży import daje pewność, że
      // ten test sprawdza faktyczną idempotencję `register()`, a nie
      // przypadkowo korzysta ze stanu ustawionego przez wcześniejszy test w
      // tym pliku (patrz test wyżej, który świadomie na tym stanie polega —
      // to jest jedyny test w pliku, który go resetuje).
      vi.resetModules();
      process.env.NEXT_RUNTIME = "nodejs";
      const { register } = await import("./instrumentation");

      await register();
      await register();

      expect(nodeSdkConstructor).toHaveBeenCalledOnce();
      expect(nodeSdkStart).toHaveBeenCalledOnce();
    });
  });

  describe("onRequestError", () => {
    it("Error — dodaje licznik z error_type równym nazwie klasy błędu", async () => {
      const { onRequestError } = await import("./instrumentation");

      await onRequestError(
        new Error("coś poszło nie tak"),
        { path: "/", method: "GET", headers: {} },
        {
          routerKind: "App Router",
          routePath: "/",
          routeType: "render",
          revalidateReason: undefined,
        },
      );

      expect(createCounter).toHaveBeenCalledWith(
        "nextjs_unhandled_errors_total",
        expect.objectContaining({ description: expect.any(String) }),
      );
      expect(counterAdd).toHaveBeenCalledWith(1, { error_type: "Error" });
    });

    it("podklasa Error (np. TypeError) — error_type to nazwa konkretnej klasy", async () => {
      const { onRequestError } = await import("./instrumentation");

      await onRequestError(
        new TypeError("zły typ"),
        { path: "/", method: "GET", headers: {} },
        {
          routerKind: "App Router",
          routePath: "/",
          routeType: "render",
          revalidateReason: undefined,
        },
      );

      expect(counterAdd).toHaveBeenCalledWith(1, { error_type: "TypeError" });
    });

    it("nie-Error (np. rzucony string) — error_type spada na 'unknown'", async () => {
      const { onRequestError } = await import("./instrumentation");

      await onRequestError(
        "zwykły string zamiast Error",
        { path: "/", method: "GET", headers: {} },
        {
          routerKind: "App Router",
          routePath: "/",
          routeType: "render",
          revalidateReason: undefined,
        },
      );

      expect(counterAdd).toHaveBeenCalledWith(1, { error_type: "unknown" });
    });
  });
});
