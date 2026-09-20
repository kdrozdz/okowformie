import { describe, expect, it } from "vitest";

import { parsePage } from "./page";

// `parsePage` parsuje `?page=` z URL-a — wejście od użytkownika/crawlera,
// więc każda wartość musi dać jednoznaczny, bezpieczny wynik (liczba
// całkowita >= 1), nigdy NaN/0/ujemną/ułamkową, którą dalej dostałby
// `getPosts()` jako numer strony.
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
    // Nie ma górnego limitu w `parsePage` samym w sobie — strona poza
    // zakresem realnych danych jest odpowiedzialnością `getPosts()`/API
    // (404 → `notFound()`), nie parsera querystringa. Kontrakt tej funkcji
    // to tylko „całkowita i dodatnia”, co ta wartość spełnia.
    const result = parsePage("99999999999999999999");

    expect(Number.isInteger(result)).toBe(true);
    expect(result).toBeGreaterThanOrEqual(1);
  });
});
