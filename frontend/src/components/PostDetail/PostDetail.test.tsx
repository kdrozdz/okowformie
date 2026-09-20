import { render } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { PostDetail as PostDetailData } from "@/lib/api/types";

import { PostDetail } from "./PostDetail";

// Patrz komentarz w `CertificatesSlider.test.tsx` — poza działającym
// serwerem Next `next/image`'s real loader traktuje każdy zdalny host jako
// nieskonfigurowany; snapshot dotyczy markupu `PostDetail`, nie pipeline'u
// optymalizacji obrazów Next.
vi.mock("next/image", () => ({
  default: (props: { src: string; alt: string; className?: string }) => {
    // eslint-disable-next-line @next/next/no-img-element
    return <img src={props.src} alt={props.alt} className={props.className} />;
  },
}));

const basePost: PostDetailData = {
  slug: "dobor-soczewek-kontaktowych",
  title: "Jak dobrać soczewki kontaktowe do pierwszej pary",
  excerpt:
    "Pierwsza wizyta po soczewki kontaktowe budzi sporo pytań — tłumaczę krok po kroku, na co zwrócić uwagę.",
  cover_image: "http://localhost:8000/media/posty/soczewki.jpg",
  cover_image_alt: "Zbliżenie na soczewkę kontaktową na opuszku palca",
  author: "Anna Kowalska",
  published_at: "2026-03-14T09:00:00Z",
  // Sanityzowany po stronie backendu (`.claude/rules/security.md`) — bezpieczny
  // do `dangerouslySetInnerHTML`, patrz też test sanityzacji HTML zgłoszony
  // do `backend-agent` w raporcie.
  content: "<p>Pierwszym krokiem jest <strong>pomiar krzywizny rogówki</strong>.</p>",
  meta_title: "Jak dobrać soczewki kontaktowe | okowFormie",
  meta_description: "Praktyczny przewodnik po pierwszym doborze soczewek kontaktowych.",
  updated_at: "2026-03-14T09:00:00Z",
  available_translations: [{ language: "en", slug: "choosing-contact-lenses" }],
};

describe("PostDetail", () => {
  it("dopasowuje snapshot z okładką (`cover_image` obecny)", () => {
    const { container } = render(<PostDetail post={basePost} lang="pl" />);

    expect(container.firstChild).toMatchSnapshot();
  });

  it("dopasowuje snapshot bez okładki (`cover_image === null` — przypadek brzegowy z `conventions.md`)", () => {
    const post: PostDetailData = { ...basePost, cover_image: null, cover_image_alt: "" };
    const { container } = render(<PostDetail post={post} lang="pl" />);

    expect(container.firstChild).toMatchSnapshot();
  });
});
