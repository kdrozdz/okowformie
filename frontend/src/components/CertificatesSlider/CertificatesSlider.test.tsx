import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { Certificate } from "@/lib/api/types";
import type { Dictionary } from "@/lib/i18n/dictionary";

import { CertificatesSlider } from "./CertificatesSlider";

// `next/image`'s real loader validates `src` against `images.remotePatterns`
// from `next.config.ts`, which only exists inside a running Next server —
// outside of it (Vitest) every remote host is "unconfigured". The lightbox
// interaction under test doesn't depend on real image optimization, so a
// plain `<img>` stand-in keeps the test focused on `CertificatesSlider`'s
// own logic instead of Next's runtime image pipeline.
vi.mock("next/image", () => ({
  default: (props: { src: string; alt: string; className?: string }) => {
    // eslint-disable-next-line @next/next/no-img-element
    return <img src={props.src} alt={props.alt} className={props.className} />;
  },
}));

const dict: Dictionary["certificates"] = {
  heading: "Moje kursy, szkolenia, certyfikaty",
  countLabel: "łącznie",
  prevAriaLabel: "Przewiń w lewo",
  nextAriaLabel: "Przewiń w prawo",
  lightboxCloseAriaLabel: "Zamknij",
  lightboxPrevAriaLabel: "Poprzedni certyfikat",
  lightboxNextAriaLabel: "Następny certyfikat",
  lightboxDialogAriaLabel: "Podgląd certyfikatu",
};

const certificates: Certificate[] = [
  { name: "Terapia widzenia I", issuer: "Krakowska Szkoła Optometrii", issued_year: 2018, image: null },
  {
    name: "Ortoptyka — kurs bazowy",
    issuer: "Warszawski Instytut Optyki Okulistycznej",
    issued_year: 2019,
    image: "http://localhost:8000/media/certyfikat-2.jpg",
  },
  {
    name: "Certyfikat optometrii",
    issuer: "Polska Akademia Kontaktologii",
    issued_year: 2020,
    image: null,
  },
];

describe("CertificatesSlider", () => {
  it("renderuje wszystkie przekazane certyfikaty", () => {
    render(<CertificatesSlider certificates={certificates} dict={dict} />);

    for (const certificate of certificates) {
      expect(screen.getByText(certificate.name)).toBeInTheDocument();
    }
  });

  it("lightbox jest domyślnie zamknięty (brak dialogu w DOM)", () => {
    render(<CertificatesSlider certificates={certificates} dict={dict} />);

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("klik na certyfikat otwiera lightbox z właściwym elementem", async () => {
    const user = userEvent.setup();
    render(<CertificatesSlider certificates={certificates} dict={dict} />);

    await user.click(screen.getByRole("button", { name: certificates[1]!.name }));

    const dialog = screen.getByRole("dialog", { name: dict.lightboxDialogAriaLabel });
    expect(
      within(dialog).getByText(`${certificates[1]!.name} — ${certificates[1]!.issuer} (2019)`),
    ).toBeInTheDocument();
  });

  it("strzałka „następny” w lightboksie przechodzi do kolejnego certyfikatu", async () => {
    const user = userEvent.setup();
    render(<CertificatesSlider certificates={certificates} dict={dict} />);

    await user.click(screen.getByRole("button", { name: certificates[0]!.name }));
    await user.click(screen.getByRole("button", { name: dict.lightboxNextAriaLabel }));

    const dialog = screen.getByRole("dialog", { name: dict.lightboxDialogAriaLabel });
    expect(
      within(dialog).getByText(`${certificates[1]!.name} — ${certificates[1]!.issuer} (2019)`),
    ).toBeInTheDocument();
  });

  it("Escape zamyka lightbox", async () => {
    const user = userEvent.setup();
    render(<CertificatesSlider certificates={certificates} dict={dict} />);

    await user.click(screen.getByRole("button", { name: certificates[0]!.name }));
    expect(screen.getByRole("dialog")).toBeInTheDocument();

    await user.keyboard("{Escape}");

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("przycisk zamknięcia (w dialogu) zamyka lightbox", async () => {
    const user = userEvent.setup();
    render(<CertificatesSlider certificates={certificates} dict={dict} />);

    await user.click(screen.getByRole("button", { name: certificates[0]!.name }));

    const dialog = screen.getByRole("dialog", { name: dict.lightboxDialogAriaLabel });
    // Backdrop i przycisk „×" w dialogu dzielą ten sam aria-label
    // (`dict.lightboxCloseAriaLabel`) — celowo, oba zamykają lightbox.
    // Scope'ujemy do dialogu, żeby kliknąć konkretnie przycisk „×", nie backdrop.
    await user.click(within(dialog).getByRole("button", { name: dict.lightboxCloseAriaLabel }));

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
});
