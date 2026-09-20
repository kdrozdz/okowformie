"use client";

/**
 * Konwencja Next.js: siatka bezpieczeństwa na wypadek, gdyby sam root
 * layout (`app/[lang]/layout.tsx` — jedyny prawdziwy root layout w tej
 * appce, patrz jego doc-komentarz) rzucił błąd, którego nie złapie żaden
 * zagnieżdżony `error.tsx` (te łapią błędy w SEGMENTACH poniżej root
 * layoutu, nie w nim samym). Musi renderować własne `<html>`/`<body>`, bo
 * w tym scenariuszu ZASTĘPUJE cały root layout, nie tylko `{children}`.
 * Zawsze poza `[lang]` (wymóg Next.js: `app/global-error.tsx`), więc brak
 * dostępu do `params`/segmentu językowego — stąd statyczny,
 * niezlokalizowany tekst.
 */
export default function GlobalError({
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <html lang="pl">
      <body>
        <h1>Something went wrong</h1>
        <p>Coś poszło nie tak. Odśwież stronę lub spróbuj ponownie.</p>
        <button type="button" onClick={() => reset()}>
          Try again / Spróbuj ponownie
        </button>
      </body>
    </html>
  );
}
