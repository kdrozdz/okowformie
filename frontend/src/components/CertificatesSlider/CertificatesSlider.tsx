"use client";

import Image from "next/image";
import { useEffect, useRef, useState } from "react";

import type { Certificate } from "@/lib/api/types";
import type { Dictionary } from "@/lib/i18n/dictionary";

import styles from "./CertificatesSlider.module.css";
import { useCertificatesLightbox } from "./useCertificatesLightbox";

interface CertificatesSliderProps {
  certificates: Certificate[];
  dict: Dictionary["certificates"];
}

// Odpowiednik `gap: 0.9rem` z `.courses__slider` w mockupie — użyte przy
// liczeniu kroku przewijania strzałkami (mockup: `offsetWidth + 14`).
const SCROLL_GAP_PX = 14;

// Lokalny odpowiednik `clsx`/`cx` — w projekcie nie ma tej zależności, a
// sklejanie klas przez template literal powtarzało się w tym pliku
// wystarczająco często, żeby uzasadnić abstrakcję (`engineering-principles.md`).
function cx(...classes: Array<string | false | undefined | null>): string {
  return classes.filter(Boolean).join(" ");
}

/**
 * Jedyny `"use client"` w tym tasku: stan lokalny (aktywny slajd, lightbox)
 * i interakcje z DOM (`scrollBy`, klawiatura) nie dają się wyrazić w Server
 * Component. Dane certyfikatów przychodzą jako propsy z `AboutSection`
 * (Server Component) — slider sam niczego nie fetchuje.
 */
export function CertificatesSlider({ certificates, dict }: CertificatesSliderProps) {
  const sliderRef = useRef<HTMLDivElement>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);
  const { lightboxIndex, isOpen, open, close, showNext, showPrev } = useCertificatesLightbox(
    certificates.length,
  );

  // Krańce przewijania — strzałka ma być wyszarzona i nieklikalna, gdy nie
  // ma już dokąd przewinąć w tym kierunku (zgłoszenie z live-testowania:
  // strzałka bez zmiany wyglądu na końcu listy sugerowała, że wciąż da się
  // kliknąć). Margines 1px pod zaokrąglenia subpikselowe scrolla.
  const [canScrollPrev, setCanScrollPrev] = useState(false);
  const [canScrollNext, setCanScrollNext] = useState(false);

  function updateScrollState() {
    const slider = sliderRef.current;
    if (!slider) return;
    const maxScrollLeft = slider.scrollWidth - slider.clientWidth;
    setCanScrollPrev(slider.scrollLeft > 1);
    setCanScrollNext(slider.scrollLeft < maxScrollLeft - 1);
  }

  useEffect(() => {
    updateScrollState();
    const slider = sliderRef.current;
    if (!slider) return;

    slider.addEventListener("scroll", updateScrollState);
    window.addEventListener("resize", updateScrollState);
    return () => {
      slider.removeEventListener("scroll", updateScrollState);
      window.removeEventListener("resize", updateScrollState);
    };
  }, [certificates.length]);

  function scrollByDirection(direction: 1 | -1) {
    const slider = sliderRef.current;
    if (!slider) return;
    const firstThumb = slider.firstElementChild as HTMLElement | null;
    const step = (firstThumb?.offsetWidth ?? 104) + SCROLL_GAP_PX;
    slider.scrollBy({ left: direction * step, behavior: "smooth" });
  }

  useEffect(() => {
    if (!isOpen) return;
    closeButtonRef.current?.focus();

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") close();
      if (event.key === "ArrowRight") showNext();
      if (event.key === "ArrowLeft") showPrev();
      // Pułapka fokusu (wzorzec WAI-ARIA dla modali): Tab/Shift+Tab nie mogą
      // wyprowadzić fokusu poza panel, mimo że overlay wizualnie zasłania
      // resztę strony — bez tego klawiatura wciąż dociera do nawigacji w tle.
      if (event.key === "Tab") handleTab(event);
    }

    function handleTab(event: KeyboardEvent) {
      const panel = panelRef.current;
      if (!panel) return;

      const focusable = panel.querySelectorAll<HTMLElement>(
        'button:not([disabled]), [href], input, select, textarea, [tabindex]:not([tabindex="-1"])',
      );
      if (focusable.length === 0) return;

      const first = focusable[0]!;
      const last = focusable[focusable.length - 1]!;
      const isInsidePanel = panel.contains(document.activeElement);

      if (event.shiftKey) {
        if (!isInsidePanel || document.activeElement === first) {
          event.preventDefault();
          last.focus();
        }
      } else if (!isInsidePanel || document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, close, showNext, showPrev]);

  const activeCertificate = lightboxIndex !== null ? certificates[lightboxIndex] : null;

  return (
    <div className={styles.sliderWrap}>
      <button
        type="button"
        className={cx(styles.arrow, styles.arrowPrev)}
        aria-label={dict.prevAriaLabel}
        onClick={() => scrollByDirection(-1)}
        disabled={!canScrollPrev}
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} aria-hidden="true">
          <path d="M15 5l-7 7 7 7" />
        </svg>
      </button>

      <div className={styles.slider} ref={sliderRef}>
        {certificates.map((certificate, index) => (
          // Index jako klucz: `Certificate` z API nie ma `id`, a
          // `name`+`issued_year` nie ma gwarancji unikalności (np. powtórzony
          // kurs w innym roku o tej samej nazwie). Bezpieczne tutaj — lista
          // to statyczny prop z serwera, nie zmienia kolejności ani nie
          // wstawia/usuwa elementów w trakcie życia komponentu po stronie
          // klienta (`.claude/commands/review.md` uwaga z /code-review).
          <button
            key={index}
            type="button"
            className={styles.certThumb}
            onClick={() => open(index)}
          >
            {certificate.image ? (
              <Image
                src={certificate.image}
                alt=""
                fill
                sizes="104px"
                className={styles.certThumbImage}
              />
            ) : (
              <CertificateIcon className={styles.certThumbIcon} />
            )}
            <span className={styles.certThumbLabel}>{certificate.name}</span>
          </button>
        ))}
      </div>

      <button
        type="button"
        className={cx(styles.arrow, styles.arrowNext)}
        aria-label={dict.nextAriaLabel}
        onClick={() => scrollByDirection(1)}
        disabled={!canScrollNext}
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} aria-hidden="true">
          <path d="M9 5l7 7-7 7" />
        </svg>
      </button>

      {activeCertificate ? (
        <div className={styles.lightbox}>
          <button
            type="button"
            className={styles.lightboxBackdrop}
            aria-label={dict.lightboxCloseAriaLabel}
            onClick={close}
          />
          <div
            ref={panelRef}
            className={styles.lightboxPanel}
            role="dialog"
            aria-modal="true"
            aria-label={dict.lightboxDialogAriaLabel}
          >
            <button
              ref={closeButtonRef}
              type="button"
              className={styles.lightboxClose}
              aria-label={dict.lightboxCloseAriaLabel}
              onClick={close}
            >
              &times;
            </button>
            <div className={styles.lightboxStage}>
              <button
                type="button"
                className={cx(styles.lightboxNav, styles.lightboxNavPrev)}
                aria-label={dict.lightboxPrevAriaLabel}
                onClick={showPrev}
              >
                &larr;
              </button>
              <div
                className={cx(
                  styles.lightboxImage,
                  !activeCertificate.image && styles.lightboxImagePlaceholder,
                )}
              >
                {activeCertificate.image ? (
                  <Image
                    src={activeCertificate.image}
                    alt={`${activeCertificate.name} — ${activeCertificate.issuer}`}
                    fill
                    sizes="(max-width: 820px) 90vw, 820px"
                    className={styles.lightboxImg}
                  />
                ) : (
                  <CertificateIcon className={styles.lightboxIcon} />
                )}
              </div>
              <button
                type="button"
                className={cx(styles.lightboxNav, styles.lightboxNavNext)}
                aria-label={dict.lightboxNextAriaLabel}
                onClick={showNext}
              >
                &rarr;
              </button>
            </div>
            <p className={styles.lightboxCaption}>
              {activeCertificate.name} — {activeCertificate.issuer} ({activeCertificate.issued_year})
            </p>
          </div>
        </div>
      ) : null}
    </div>
  );
}

function CertificateIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.6}
      aria-hidden="true"
    >
      <rect x="4" y="3" width="16" height="13" rx="2" />
      <path d="M8 7h8M8 10h5" />
      <path d="M9 16v4l3-1.5L15 20v-4" />
    </svg>
  );
}
