import { describe, expect, it } from "vitest";

import { parsePage } from "./page";

// Ta sama logika co `posty/page.tsx: parsePage`, ale własny test — komponent
// z logiką wymaga własnego pokrycia, nie importu testów innej strony
// (`.claude/rules/conventions.md`).
describe("parsePage", () => {
  it("brak parametru → strona 1", () => {
    expect(parsePage(undefined)).toBe(1);
  });

  it('"1" → strona 1', () => {
    expect(parsePage("1")).toBe(1);
  });

  it('"2" → strona 2', () => {
    expect(parsePage("2")).toBe(2);
  });

  it('"0" → strona 1 (0 nie jest poprawnym numerem strony)', () => {
    expect(parsePage("0")).toBe(1);
  });

  it('"-1" → strona 1 (wartości ujemne odrzucone)', () => {
    expect(parsePage("-1")).toBe(1);
  });

  it('"abc" → strona 1 (NaN odrzucone)', () => {
    expect(parsePage("abc")).toBe(1);
  });

  it('"1.5" → strona 1 (wartości ułamkowe odrzucone)', () => {
    expect(parsePage("1.5")).toBe(1);
  });

  it('pusty string → strona 1 (Number("") === 0)', () => {
    expect(parsePage("")).toBe(1);
  });

  it("bardzo duża liczba jako string → liczba całkowita ≥ 1, przepuszczona bez zawieszenia", () => {
    const result = parsePage("99999999999999999999");

    expect(Number.isInteger(result)).toBe(true);
    expect(result).toBeGreaterThanOrEqual(1);
  });
});
