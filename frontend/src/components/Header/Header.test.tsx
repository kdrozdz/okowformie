import { render } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { Header } from "./Header";

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

describe("Header", () => {
  it("dopasowuje snapshot z dostępnym imieniem i nazwiskiem autorki (`about.full_name` z API)", () => {
    const { container } = render(<Header lang="pl" authorName="Anna Kowalska" />);

    expect(container.firstChild).toMatchSnapshot();
  });

  it("dopasowuje snapshot bez imienia i nazwiska (tłumaczenie „O mnie” niepublikowane/niedostępne — nie blokuje renderu headera)", () => {
    const { container } = render(<Header lang="en" authorName={null} />);

    expect(container.firstChild).toMatchSnapshot();
  });
});
