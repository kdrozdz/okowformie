import { useCallback, useState } from "react";

export interface CertificatesLightboxControls {
  /** `null` = zamknięty. */
  lightboxIndex: number | null;
  isOpen: boolean;
  open: (index: number) => void;
  close: () => void;
  showNext: () => void;
  showPrev: () => void;
}

/**
 * Czysta logika stanu lightboxa (indeks, otwarcie/zamknięcie, nawigacja
 * cykliczna) — bez zależności od DOM, żeby dało się przetestować
 * niezależnie od `CertificatesSlider` (Vitest, bez renderowania komponentu).
 */
export function useCertificatesLightbox(count: number): CertificatesLightboxControls {
  const [lightboxIndex, setLightboxIndex] = useState<number | null>(null);

  const open = useCallback(
    (index: number) => {
      if (index < 0 || index >= count) return;
      setLightboxIndex(index);
    },
    [count],
  );

  const close = useCallback(() => {
    setLightboxIndex(null);
  }, []);

  const showNext = useCallback(() => {
    if (count === 0) return;
    setLightboxIndex((current) => (current === null ? null : (current + 1) % count));
  }, [count]);

  const showPrev = useCallback(() => {
    if (count === 0) return;
    setLightboxIndex((current) => (current === null ? null : (current - 1 + count) % count));
  }, [count]);

  return { lightboxIndex, isOpen: lightboxIndex !== null, open, close, showNext, showPrev };
}
