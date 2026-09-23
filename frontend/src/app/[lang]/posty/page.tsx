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

export async function generateMetadata({ params, searchParams }: PostsPageProps): Promise<Metadata> {
  const { lang } = await params;
  if (!isSupportedLanguage(lang)) return {};

  const { page: rawPage } = await searchParams;
  const page = parsePage(rawPage);

  // Self-referencing canonical per stronę paginacji — kanonizacja wszystkich
  // stron do strony 1 odcina Google ścieżkę crawlowania do treści na
  // kolejnych stronach (aktualna wytyczna Google, sprawdzona przy audycie
  // tego taska). Endpoint listy nie zwraca meta_title/meta_description
  // (oczekiwane, nie brakujący endpoint) — statyczne metadane per język.
  const dict = getDictionary(lang).posts;
  const canonicalPath = page > 1 ? `/${lang}/posty?page=${page}` : `/${lang}/posty`;

  return {
    title: dict.metaTitle,
    description: dict.metaDescription,
    alternates: {
      canonical: canonicalPath,
      // hreflang tylko na stronie 1: to jedyna strona listy gwarantowana w
      // obu językach. Przy różnej liczbie stron per język (dziś: EN ma
      // tylko 1 post = 1 strona) nie da się bez dodatkowego zapytania do
      // API drugiego języka bezpiecznie założyć, że odpowiadająca strona
      // istnieje — pomijamy `languages` zamiast zgadywać.
      ...(page === 1
        ? {
            languages: {
              pl: "/pl/posty",
              en: "/en/posty",
              "x-default": "/pl/posty",
            },
          }
        : {}),
    },
    openGraph: {
      type: "website",
      title: dict.metaTitle,
      description: dict.metaDescription,
      url: canonicalPath,
    },
    twitter: {
      card: "summary_large_image",
      title: dict.metaTitle,
      description: dict.metaDescription,
    },
  };
}

/** Eksportowana dla testów jednostkowych (`page.test.ts`) — reszta modułu jest RSC. */
export function parsePage(raw: string | undefined): number {
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
        basePath={`/${lang}/posty`}
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
