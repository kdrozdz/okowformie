import { render } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { About, Certificate } from "@/lib/api/types";

import { AboutSection } from "./AboutSection";

// Patrz komentarz w `CertificatesSlider.test.tsx` — poza działającym
// serwerem Next `next/image`'s real loader traktuje każdy zdalny host jako
// nieskonfigurowany; snapshot dotyczy markupu `AboutSection` (i osadzonego
// `CertificatesSlider`), nie pipeline'u optymalizacji obrazów Next.
vi.mock("next/image", () => ({
  default: (props: { src: string; alt: string; className?: string }) => {
    // eslint-disable-next-line @next/next/no-img-element
    return <img src={props.src} alt={props.alt} className={props.className} />;
  },
}));

const certificates: Certificate[] = [
  { name: "Terapia widzenia I", issuer: "Krakowska Szkoła Optometrii", issued_year: 2018, image: null },
  {
    name: "Ortoptyka — kurs bazowy",
    issuer: "Warszawski Instytut Optyki Okulistycznej",
    issued_year: 2019,
    image: "http://localhost:8000/media/certyfikat-2.jpg",
  },
];

const baseAbout: About = {
  full_name: "Anna Kowalska",
  headline: "Optometrystka, terapeutka widzenia",
  bio: "<p>Od 10 lat pomagam pacjentom dobrać soczewki kontaktowe i okulary.</p>",
  photo: "http://localhost:8000/media/anna-kowalska.jpg",
  photo_alt: "Portret Anny Kowalskiej",
  meta_title: "O mnie | okowFormie",
  meta_description: "Poznaj Annę Kowalską, optometrystkę i autorkę bloga okowFormie.",
  updated_at: "2026-03-01T09:00:00Z",
  available_translations: [{ language: "en" }],
  certificates,
};

describe("AboutSection", () => {
  it("dopasowuje snapshot ze zdjęciem i certyfikatami", () => {
    // `asFragment()`, nie `container.firstChild`: komponent renderuje
    // Fragment z kilkoma sąsiadującymi korzeniami (`<h1>`, `div.about`,
    // opcjonalnie `div.courses`) — `.firstChild` łapałby tylko `<h1>` i
    // milcząco pomijał resztę markupu, którą ten test ma pokrywać.
    const { asFragment } = render(<AboutSection about={baseAbout} lang="pl" />);

    expect(asFragment()).toMatchSnapshot();
  });

  it("dopasowuje snapshot bez zdjęcia (`photo === null` — placeholder SVG zamiast `<Image>`)", () => {
    const about: About = { ...baseAbout, photo: null, photo_alt: "" };
    const { asFragment } = render(<AboutSection about={about} lang="pl" />);

    expect(asFragment()).toMatchSnapshot();
  });

  it("dopasowuje snapshot bez certyfikatów (`certificates: []` — sekcja kursów/certyfikatów całkowicie pominięta)", () => {
    const about: About = { ...baseAbout, certificates: [] };
    const { asFragment } = render(<AboutSection about={about} lang="pl" />);

    expect(asFragment()).toMatchSnapshot();
  });
});
