import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { Download } from "@/lib/api/types";

import { DownloadList } from "./DownloadList";

const downloads: Download[] = [
  {
    title: "Ćwiczenia dla oczu",
    description: "Zestaw ćwiczeń relaksujących wzrok po pracy przy ekranie.",
    file: "http://backend:8000/media/downloads/files/abc123.pdf",
    order: 0,
  },
  {
    title: "Ulotka: dobór soczewek",
    description: "",
    file: "http://backend:8000/media/downloads/files/def456.pdf",
    order: 1,
  },
];

describe("DownloadList", () => {
  it("renderuje komunikat o pustej liście, gdy brak plików (pusty stan, nie błąd)", () => {
    render(
      <DownloadList
        downloads={[]}
        downloadLabel="Pobierz plik"
        downloadErrorMessage="Nie udało się pobrać pliku."
        emptyMessage="Brak plików do pobrania."
      />,
    );

    expect(screen.getByText("Brak plików do pobrania.")).toBeInTheDocument();
    expect(screen.queryByRole("list")).not.toBeInTheDocument();
  });

  it("renderuje tytuł, opis i link pobierania dla każdego pliku", () => {
    render(
      <DownloadList
        downloads={downloads}
        downloadLabel="Pobierz plik"
        downloadErrorMessage="Nie udało się pobrać pliku."
        emptyMessage="Brak plików."
      />,
    );

    expect(screen.getByRole("heading", { name: "Ćwiczenia dla oczu" })).toBeInTheDocument();
    expect(
      screen.getByText("Zestaw ćwiczeń relaksujących wzrok po pracy przy ekranie."),
    ).toBeInTheDocument();

    // `aria-label` niesie tytuł pliku — bez tego czytnik ekranu w trybie
    // "lista linków" odczytałby "Pobierz plik" tyle razy, ile jest pozycji,
    // bez możliwości ich rozróżnienia. Rzeczywiste pobieranie (fetch → blob,
    // czytelna nazwa pliku) to zachowanie `DownloadButton`, przetestowane
    // osobno w `DownloadButton.test.tsx` — tu sprawdzamy tylko, że
    // `DownloadList` przekazuje mu właściwy `href`/etykietę.
    const firstLink = screen.getByRole("link", { name: "Pobierz plik: Ćwiczenia dla oczu" });
    expect(firstLink).toHaveAttribute("href", "http://backend:8000/media/downloads/files/abc123.pdf");

    expect(
      screen.getByRole("link", { name: "Pobierz plik: Ulotka: dobór soczewek" }),
    ).toBeInTheDocument();
  });

  it("nie renderuje pustego akapitu opisu, gdy `description` jest pustym stringiem", () => {
    render(
      <DownloadList
        downloads={[downloads[1]]}
        downloadLabel="Pobierz plik"
        downloadErrorMessage="Nie udało się pobrać pliku."
        emptyMessage="Brak plików."
      />,
    );

    expect(screen.getByRole("heading", { name: "Ulotka: dobór soczewek" })).toBeInTheDocument();
    // Tylko nagłówek — brak dodatkowego <p> dla pustego opisu.
    const card = screen.getByRole("heading", { name: "Ulotka: dobór soczewek" }).closest("li");
    expect(card?.querySelectorAll("p")).toHaveLength(0);
  });
});
