"use client";

import { useRef, useState } from "react";

interface DownloadButtonProps {
  fileUrl: string;
  filename: string;
  label: string;
  ariaLabel: string;
  className: string;
  /** Komunikat pod linkiem, gdy fetch zawiedzie i zadziała fallback `window.open`. */
  errorMessage: string;
  errorClassName: string;
  /**
   * Klasa kontenera wokół linku i komunikatu błędu. Konieczna, żeby oba
   * razem pozostały JEDNYM flex-itemem karty w `DownloadList` — bez tego
   * kontenera Fragment renderuje `<a>` i `<p role="alert">` jako dwa
   * osobne dzieci `.card`, co przy `justify-content: space-between` na
   * desktopie rozjeżdża przycisk i komunikat błędu po przeciwnych
   * krawędziach karty (znalezisko z review `qa-agent`).
   */
  wrapperClassName: string;
}

/**
 * Link pobierania jako mała klient-side wysepka (reszta `DownloadList`
 * zostaje server component). Konieczne: `download.file` jest absolutnym
 * URL-em na innej domenie niż frontend (backend/storage), a przeglądarki
 * **ignorują atrybut `download` dla linków cross-origin** — zwykły `<a
 * href download>` w tym wypadku po prostu nawiguje/otwiera plik zamiast go
 * pobrać, więc użytkownik "wychodzi" ze strony. Jedyny sposób wymuszenia
 * realnego zapisu na dysk niezależnie od originu: pobrać treść przez
 * `fetch`, zbudować z niej `blob:` URL (zawsze same-origin względem
 * dokumentu, który go stworzył) i kliknąć w niego programowo.
 *
 * `href={fileUrl}` zostaje na elemencie mimo `onClick` — zapewnia sensowne
 * zachowanie bez JS (SSR/wyłączony JS), middle-click/ctrl-click (otwiera
 * plik wprost w nowej karcie, React `onClick` nie łapie tych kliknięć) i
 * "Kopiuj adres linku" w menu kontekstowym.
 */
export function DownloadButton({
  fileUrl,
  filename,
  label,
  ariaLabel,
  className,
  errorMessage,
  errorClassName,
  wrapperClassName,
}: DownloadButtonProps) {
  const isDownloadingRef = useRef(false);
  const [hasError, setHasError] = useState(false);

  async function handleClick(event: React.MouseEvent<HTMLAnchorElement>) {
    event.preventDefault();
    if (isDownloadingRef.current) {
      return;
    }
    isDownloadingRef.current = true;
    setHasError(false);

    try {
      const response = await fetch(fileUrl);
      if (!response.ok) {
        throw new Error(`Pobieranie pliku nie powiodło się: ${response.status} ${fileUrl}`);
      }
      const blob = await response.blob();
      const blobUrl = URL.createObjectURL(blob);
      try {
        const link = document.createElement("a");
        link.href = blobUrl;
        link.download = filename;
        link.click();
      } finally {
        URL.revokeObjectURL(blobUrl);
      }
    } catch (error) {
      // Nie połykamy błędu bez decyzji, co dalej (`.claude/rules/code-quality.md`)
      // — użytkownik i tak ma dostać plik, więc fallback to zachowanie
      // natywnego linku (nowa karta), nie cichy brak reakcji na klik.
      // `setHasError` dokłada widoczny komunikat obok `console.error`:
      // sam fallback (otwarcie w nowej karcie zamiast pobrania) jest łatwy
      // do przeoczenia bez wyraźnej informacji, co się stało.
      console.error("Nie udało się pobrać pliku przez fetch, otwieram bezpośrednio:", error);
      window.open(fileUrl, "_blank", "noopener,noreferrer");
      setHasError(true);
    } finally {
      isDownloadingRef.current = false;
    }
  }

  return (
    <div className={wrapperClassName}>
      <a href={fileUrl} onClick={handleClick} aria-label={ariaLabel} className={className}>
        {label}
      </a>
      {hasError ? (
        <p role="alert" className={errorClassName}>
          {errorMessage}
        </p>
      ) : null}
    </div>
  );
}
