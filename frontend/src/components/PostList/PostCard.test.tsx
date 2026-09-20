import { render } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { PostSummary } from "@/lib/api/types";

import { PostCard } from "./PostCard";

// Patrz komentarz w `CertificatesSlider.test.tsx` — poza działającym
// serwerem Next `next/image`'s real loader traktuje każdy zdalny host jako
// nieskonfigurowany; snapshot dotyczy markupu `PostCard`, nie pipeline'u
// optymalizacji obrazów Next.
vi.mock("next/image", () => ({
  default: (props: { src: string; alt: string; className?: string }) => {
    // eslint-disable-next-line @next/next/no-img-element
    return <img src={props.src} alt={props.alt} className={props.className} />;
  },
}));

const basePost: PostSummary = {
  slug: "dobor-soczewek-kontaktowych",
  title: "Jak dobrać soczewki kontaktowe do pierwszej pary",
  excerpt:
    "Pierwsza wizyta po soczewki kontaktowe budzi sporo pytań — tłumaczę krok po kroku, na co zwrócić uwagę.",
  cover_image: "http://localhost:8000/media/posty/soczewki.jpg",
  cover_image_alt: "Zbliżenie na soczewkę kontaktową na opuszku palca",
  author: "Anna Kowalska",
  published_at: "2026-03-14T09:00:00Z",
};

describe("PostCard", () => {
  it("dopasowuje snapshot z okładką (`cover_image` obecny)", () => {
    const { container } = render(<PostCard post={basePost} lang="pl" />);

    expect(container.firstChild).toMatchSnapshot();
  });

  it("dopasowuje snapshot bez okładki (`cover_image === null` — brak obrazu okładki, przypadek brzegowy z `conventions.md`)", () => {
    const post: PostSummary = { ...basePost, cover_image: null, cover_image_alt: "" };
    const { container } = render(<PostCard post={post} lang="pl" />);

    expect(container.firstChild).toMatchSnapshot();
  });
});
