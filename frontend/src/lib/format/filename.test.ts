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

  it("dla tytułu bez żadnych znaków alfanumerycznych podstawia domyślną nazwę", () => {
    expect(downloadFilename("★★★", "https://example.com/a.pdf")).toBe("plik.pdf");
  });

  it("zachowuje rozszerzenie niezależnie od wielkości liter w URL-u", () => {
    expect(downloadFilename("Cennik", "https://example.com/a.PDF")).toBe("cennik.pdf");
  });
});
