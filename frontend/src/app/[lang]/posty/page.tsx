import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { Pagination } from "@/components/Pagination/Pagination";
import { PostList } from "@/components/PostList/PostList";
import { getPosts } from "@/lib/api/client";
import { getDictionary } from "@/lib/i18n/dictionary";
import { isSupportedLanguage } from "@/lib/i18n/languages";

interface PostsPageProps {
  params: Promise<{ lang: string }>;
  searchParams: Promise<{ page?: string }>;
}

export async function generateMetadata({ params }: PostsPageProps): Promise<Metadata> {
  const { lang } = await params;
  if (!isSupportedLanguage(lang)) return {};

  // Endpoint listy nie zwraca meta_title/meta_description (oczekiwane, nie
  // brakujący endpoint) — statyczne metadane per język.
  const dict = getDictionary(lang).posts;

  return {
    title: dict.metaTitle,
    description: dict.metaDescription,
    alternates: {
      canonical: `/${lang}/posty`,
      // Statyczna mapa: obie trasy listy istnieją niezależnie od zawartości.
      languages: {
        pl: "/pl/posty",
        en: "/en/posty",
        "x-default": "/pl/posty",
      },
    },
    openGraph: {
      type: "website",
      title: dict.metaTitle,
      description: dict.metaDescription,
      url: `/${lang}/posty`,
    },
    twitter: {
      card: "summary_large_image",
      title: dict.metaTitle,
      description: dict.metaDescription,
    },
  };
}

function parsePage(raw: string | undefined): number {
  const parsed = Number(raw);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : 1;
}

export default async function PostsPage({ params, searchParams }: PostsPageProps) {
  const { lang } = await params;
  if (!isSupportedLanguage(lang)) {
    notFound();
  }

  const { page: rawPage } = await searchParams;
  const page = parsePage(rawPage);

  // Strona 1 zawsze istnieje (pusta lista to poprawny stan, nie 404).
  // Strona poza zakresem paginacji → API zwraca 404 → `notFound()`, tak
  // samo jak nieistniejący slug.
  const result = await getPosts(lang, page);
  if (!result) {
    notFound();
  }

  const dict = getDictionary(lang).posts;

  return (
    <>
      <h1 className="page-title">{dict.heading}</h1>
      <PostList posts={result.results} lang={lang} emptyMessage={dict.empty} />
      <Pagination
        lang={lang}
        currentPage={page}
        hasPrevious={Boolean(result.previous)}
        hasNext={Boolean(result.next)}
        previousLabel={dict.previousPage}
        nextLabel={dict.nextPage}
        ariaLabel={dict.paginationAriaLabel}
      />
    </>
  );
}
