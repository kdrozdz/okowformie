import { render } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

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

describe("Footer", () => {
  it("dopasowuje snapshot (PL)", () => {
    const { container } = render(<Footer lang="pl" />);

    expect(container.firstChild).toMatchSnapshot();
  });

  it("dopasowuje snapshot (EN) — inny słownik, ten sam markup", () => {
    const { container } = render(<Footer lang="en" />);

    expect(container.firstChild).toMatchSnapshot();
  });
});
