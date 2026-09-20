import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { Branding } from "@/lib/api/types";

import { Header } from "./Header";
import styles from "./Header.module.css";

// Patrz komentarz w `CertificatesSlider.test.tsx` — poza działającym
// serwerem Next `next/image`'s real loader traktuje każdy zdalny host jako
// nieskonfigurowany; snapshot dotyczy markupu `Header`, nie pipeline'u
// optymalizacji obrazów Next.
vi.mock("next/image", () => ({
  default: (props: { src: string; alt: string; className?: string }) => {
    // eslint-disable-next-line @next/next/no-img-element
    return <img src={props.src} alt={props.alt} className={props.className} />;
  },
}));

// `PrimaryNav` (dziecko `Header`) jest `"use client"` i wywołuje
// `usePathname()` z `next/navigation` — poza routerem Next (Vitest/jsdom)
// nie ma dostawcy tego kontekstu, więc bez mocka `usePathname()` zwraca
// `null` i komponent rzuca przy próbie `.startsWith()` na nim. Ustalona
// ścieżka trzyma snapshot deterministycznym niezależnie od tego, skąd
// faktycznie renderowalibyśmy w przeglądarce.
vi.mock("next/navigation", () => ({
  usePathname: () => "/pl/o-mnie",
}));

const fullBranding: Branding = {
  logo: "http://backend:8000/media/branding/logo/abc123.png",
  social_links: [
    { platform: "linkedin", url: "https://www.linkedin.com/company/okowformie" },
    { platform: "instagram", url: "https://www.instagram.com/okowformie" },
    { platform: "facebook", url: "https://www.facebook.com/okowformie" },
  ],
};

describe("Header", () => {
  it("dopasowuje snapshot z dostępnym imieniem i nazwiskiem autorki (`about.full_name` z API) oraz pełnym brandingiem (logo + 3 linki social)", () => {
    const { container } = render(
      <Header lang="pl" authorName="Anna Kowalska" branding={fullBranding} />,
    );

    expect(container.firstChild).toMatchSnapshot();
  });

  it("dopasowuje snapshot bez imienia i nazwiska (tłumaczenie „O mnie” niepublikowane/niedostępne — nie blokuje renderu headera) oraz z pełnym brandingiem", () => {
    const { container } = render(<Header lang="en" authorName={null} branding={fullBranding} />);

    expect(container.firstChild).toMatchSnapshot();
  });

  it("dopasowuje snapshot z `branding: null` (błąd pobrania) — fallback na statyczne `/brand/logo.png`, bez linków social", () => {
    const { container } = render(<Header lang="pl" authorName="Anna Kowalska" branding={null} />);

    expect(container.firstChild).toMatchSnapshot();
  });

  it("dopasowuje snapshot z pustą `social_links` (panel jeszcze nieskonfigurowany) — logo z API, bez linków social", () => {
    const { container } = render(
      <Header
        lang="pl"
        authorName="Anna Kowalska"
        branding={{ logo: fullBranding.logo, social_links: [] }}
      />,
    );

    expect(container.firstChild).toMatchSnapshot();
  });

  it("pomija platformę spoza rejestru (np. `tiktok`) bez wywalania renderu, zachowując resztę headera", () => {
    const { container } = render(
      <Header
        lang="pl"
        authorName="Anna Kowalska"
        branding={{
          logo: fullBranding.logo,
          social_links: [
            { platform: "linkedin", url: "https://www.linkedin.com/company/okowformie" },
            { platform: "tiktok", url: "https://www.tiktok.com/@okowformie" },
          ],
        }}
      />,
    );

    // Nieznana platforma nie trafia do renderu — brak linku do jej URL-a
    // i tylko jeden link social w `.brandSocial` (ten dla `linkedin`).
    expect(screen.queryByRole("link", { name: /tiktok/i })).not.toBeInTheDocument();
    const socialLinks = container.querySelectorAll(`.${styles.brandSocial} a`);
    expect(socialLinks).toHaveLength(1);
    expect(socialLinks[0]).toHaveAttribute(
      "href",
      "https://www.linkedin.com/company/okowformie",
    );

    // Reszta headera renderuje się normalnie — logo, wordmark, nawigacja.
    expect(screen.getByRole("link", { name: "okowFormie — strona główna" })).toHaveAttribute(
      "href",
      "/pl/o-mnie",
    );
    expect(screen.getByRole("navigation", { name: "Sekcje strony" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "okowFormie na LinkedIn" })).toBeInTheDocument();
  });
});
