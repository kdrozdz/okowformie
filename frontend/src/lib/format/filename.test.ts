import { describe, expect, it } from "vitest";

import { downloadFilename } from "./filename";

describe("downloadFilename", () => {
  it("zamienia tytuł na slug i doklejа rozszerzenie z URL-a pliku", () => {
    expect(downloadFilename("Cennik usług", "https://example.com/media/downloads/files/abc123.pdf")).toBe(
      "cennik-uslug.pdf",
    );
  });

  it("obsługuje wszystkie polskie znaki specjalne", () => {
    expect(downloadFilename("Ćma źrebię łąka jeż", "https://example.com/a.pdf")).toBe(
      "cma-zrebie-laka-jez.pdf",
    );
  });

  it("usuwa znaki interpunkcyjne i wielokrotne spacje", () => {
    expect(downloadFilename("  Regulamin: wizyty (2026)!  ", "https://example.com/a.pdf")).toBe(
      "regulamin-wizyty-2026.pdf",
    );
  });

  it("dla tytułu bez żadnych znaków alfanumerycznych wraca do oryginalnej nazwy ze storage (unikalnej), zamiast kolizyjnej stałej", () => {
    expect(downloadFilename("★★★", "https://example.com/media/downloads/files/abc123.pdf")).toBe(
      "abc123.pdf",
    );
    expect(downloadFilename("★★★", "https://example.com/media/downloads/files/def456.pdf")).toBe(
      "def456.pdf",
    );
  });

  it("zachowuje rozszerzenie niezależnie od wielkości liter w nazwie pliku", () => {
    expect(downloadFilename("Cennik", "https://example.com/a.PDF")).toBe("cennik.pdf");
  });

  it("nie wywala się na relatywnym albo zdeformowanym URL-u (np. źle skonfigurowane SITE_URL) — nie używa `new URL()`", () => {
    expect(downloadFilename("Cennik", "/media/downloads/files/abc123.pdf")).toBe("cennik.pdf");
    expect(downloadFilename("Cennik", "nie-jest-to-poprawny-url")).toBe("cennik");
  });

  it("ucina query string i fragment przy wyciąganiu oryginalnej nazwy/rozszerzenia", () => {
    expect(downloadFilename("★★★", "https://example.com/media/downloads/files/abc123.pdf?x=1#y")).toBe(
      "abc123.pdf",
    );
  });
});
