import { render } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { Branding } from "@/lib/api/types";

import { Footer } from "./Footer";

// Patrz komentarz w `CertificatesSlider.test.tsx` — poza działającym
// serwerem Next `next/image`'s real loader traktuje każdy zdalny host jako
// nieskonfigurowany; snapshot dotyczy markupu `Footer`, nie pipeline'u
// optymalizacji obrazów Next.
vi.mock("next/image", () => ({
  default: (props: { src: string; alt: string; className?: string }) => {
    // eslint-disable-next-line @next/next/no-img-element
    return <img src={props.src} alt={props.alt} className={props.className} />;
  },
}));

const fullBranding: Branding = {
  logo: "http://backend:8000/media/branding/logo/abc123.png",
  social_links: [],
};

describe("Footer", () => {
  it("dopasowuje snapshot (PL) — logo z API", () => {
    const { container } = render(<Footer lang="pl" branding={fullBranding} />);

    expect(container.firstChild).toMatchSnapshot();
  });

  it("dopasowuje snapshot (EN) — inny słownik, ten sam markup, logo z API", () => {
    const { container } = render(<Footer lang="en" branding={fullBranding} />);

    expect(container.firstChild).toMatchSnapshot();
  });

  it("dopasowuje snapshot z `branding: null` (błąd pobrania) — fallback na statyczne `/brand/logo.png`", () => {
    const { container } = render(<Footer lang="pl" branding={null} />);

    expect(container.firstChild).toMatchSnapshot();
  });
});
