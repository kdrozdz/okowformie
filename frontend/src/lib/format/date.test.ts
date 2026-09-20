import { describe, expect, it } from "vitest";

import { formatDate } from "./date";

describe("formatDate", () => {
  it("formatuje datę po polsku (dzień, miesiąc słownie, rok)", () => {
    expect(formatDate("2026-09-12T10:00:00Z", "pl")).toBe("12 września 2026");
  });

  it("formatuje datę po angielsku", () => {
    expect(formatDate("2026-09-12T10:00:00Z", "en")).toBe("September 12, 2026");
  });

  it("używa strefy Europe/Warsaw zamiast strefy środowiska uruchomienia — czas tuż przed północą UTC nie przeskakuje na następny dzień", () => {
    // 23:30 UTC 30 września = 01:30 CEST 1 października w Warszawie latem —
    // gdyby formatowanie używało UTC zamiast Europe/Warsaw, wynik pokazałby
    // wciąż 30 września (dokładnie ten błąd hydratacji, który ten test pilnuje).
    expect(formatDate("2026-06-30T23:30:00Z", "pl")).toBe("1 lipca 2026");
  });
});
