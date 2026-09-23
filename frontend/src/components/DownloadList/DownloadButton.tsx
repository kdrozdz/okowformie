"use client";

import { useRef } from "react";

interface DownloadButtonProps {
  fileUrl: string;
  filename: string;
  label: string;
  ariaLabel: string;
  className: string;
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
export function DownloadButton({ fileUrl, filename, label, ariaLabel, className }: DownloadButtonProps) {
  const isDownloadingRef = useRef(false);

  async function handleClick(event: React.MouseEvent<HTMLAnchorElement>) {
    event.preventDefault();
    if (isDownloadingRef.current) {
      return;
    }
    isDownloadingRef.current = true;

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
      console.error("Nie udało się pobrać pliku przez fetch, otwieram bezpośrednio:", error);
      window.open(fileUrl, "_blank", "noopener,noreferrer");
    } finally {
      isDownloadingRef.current = false;
    }
  }

  return (
    <a href={fileUrl} onClick={handleClick} aria-label={ariaLabel} className={className}>
      {label}
    </a>
  );
}
