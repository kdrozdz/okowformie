import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { DownloadButton } from "./DownloadButton";

describe("DownloadButton", () => {
  let clickSpy: ReturnType<typeof vi.spyOn>;
  let createObjectURLMock: ReturnType<typeof vi.fn>;
  let revokeObjectURLMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    // jsdom nie implementuje `HTMLAnchorElement.click()` nawigacji ani
    // `URL.createObjectURL`/`revokeObjectURL` — mockowane, żeby przetestować
    // zachowanie bez prawdziwej nawigacji/blobów.
    clickSpy = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
    createObjectURLMock = vi.fn(() => "blob:mock-url");
    revokeObjectURLMock = vi.fn();
    vi.stubGlobal("URL", { ...URL, createObjectURL: createObjectURLMock, revokeObjectURL: revokeObjectURLMock });
    vi.stubGlobal("open", vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("pobiera plik przez fetch i klika w blob URL z czytelną nazwą, zamiast nawigować do oryginalnego linku", async () => {
    const blob = new Blob(["%PDF-1.4"], { type: "application/pdf" });
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({ ok: true, status: 200, blob: () => Promise.resolve(blob) }),
    );
    const user = userEvent.setup();

    render(
      <DownloadButton
        fileUrl="https://backend.example.com/media/downloads/files/abc123.pdf"
        filename="cennik-uslug.pdf"
        label="Pobierz plik"
        ariaLabel="Pobierz plik: Cennik usług"
        className="link"
        errorMessage="Nie udało się pobrać pliku."
        errorClassName="error"
        wrapperClassName="wrapper"
      />,
    );

    await user.click(screen.getByRole("link", { name: "Pobierz plik: Cennik usług" }));

    expect(fetch).toHaveBeenCalledWith("https://backend.example.com/media/downloads/files/abc123.pdf");
    expect(createObjectURLMock).toHaveBeenCalledWith(blob);
    // Element kliknięty programowo (nie kliknięty przez usera) to ten
    // stworzony przez `document.createElement("a")` w handlerze — jedyny
    // sposób odróżnienia go od anchora renderowanego przez komponent to
    // sprawdzenie, na jakim elemencie faktycznie wylądował `download`/`href`
    // w momencie wywołania `.click()`.
    expect(clickSpy).toHaveBeenCalledTimes(1);
    const clickedElement = clickSpy.mock.contexts[0] as HTMLAnchorElement;
    expect(clickedElement.href).toBe("blob:mock-url");
    expect(clickedElement.download).toBe("cennik-uslug.pdf");
    expect(revokeObjectURLMock).toHaveBeenCalledWith("blob:mock-url");
    expect(window.open).not.toHaveBeenCalled();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("gdy fetch zawiedzie, nie zostawia martwego przycisku — otwiera oryginalny plik w nowej karcie i pokazuje widoczny błąd", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("network error")));
    vi.spyOn(console, "error").mockImplementation(() => {});
    const user = userEvent.setup();

    render(
      <DownloadButton
        fileUrl="https://backend.example.com/media/downloads/files/abc123.pdf"
        filename="cennik-uslug.pdf"
        label="Pobierz plik"
        ariaLabel="Pobierz plik: Cennik usług"
        className="link"
        errorMessage="Nie udało się pobrać pliku."
        errorClassName="error"
        wrapperClassName="wrapper"
      />,
    );

    await user.click(screen.getByRole("link", { name: "Pobierz plik: Cennik usług" }));

    expect(window.open).toHaveBeenCalledWith(
      "https://backend.example.com/media/downloads/files/abc123.pdf",
      "_blank",
      "noopener,noreferrer",
    );
    // Bez tego użytkownik nie ma żadnej wskazówki, że plik otworzył się w
    // nowej karcie zamiast się pobrać (fallback jest łatwy do przeoczenia).
    expect(screen.getByRole("alert")).toHaveTextContent("Nie udało się pobrać pliku.");
  });

  it("gdy backend odpowie błędem HTTP, otwiera oryginalny plik w nowej karcie zamiast pobrać treść błędu jako plik", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 500 }));
    vi.spyOn(console, "error").mockImplementation(() => {});
    const user = userEvent.setup();

    render(
      <DownloadButton
        fileUrl="https://backend.example.com/media/downloads/files/abc123.pdf"
        filename="cennik-uslug.pdf"
        label="Pobierz plik"
        ariaLabel="Pobierz plik: Cennik usług"
        className="link"
        errorMessage="Nie udało się pobrać pliku."
        errorClassName="error"
        wrapperClassName="wrapper"
      />,
    );

    await user.click(screen.getByRole("link", { name: "Pobierz plik: Cennik usług" }));

    expect(createObjectURLMock).not.toHaveBeenCalled();
    expect(window.open).toHaveBeenCalledWith(
      "https://backend.example.com/media/downloads/files/abc123.pdf",
      "_blank",
      "noopener,noreferrer",
    );
    expect(screen.getByRole("alert")).toHaveTextContent("Nie udało się pobrać pliku.");
  });

  it("renderuje realny `href` do oryginalnego pliku — fallback dla braku JS, middle-click i „kopiuj link”", () => {
    render(
      <DownloadButton
        fileUrl="https://backend.example.com/media/downloads/files/abc123.pdf"
        filename="cennik-uslug.pdf"
        label="Pobierz plik"
        ariaLabel="Pobierz plik: Cennik usług"
        className="link"
        errorMessage="Nie udało się pobrać pliku."
        errorClassName="error"
        wrapperClassName="wrapper"
      />,
    );

    expect(screen.getByRole("link", { name: "Pobierz plik: Cennik usług" })).toHaveAttribute(
      "href",
      "https://backend.example.com/media/downloads/files/abc123.pdf",
    );
  });
});
