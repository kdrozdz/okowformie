import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { DownloadList } from "@/components/DownloadList/DownloadList";
import { Pagination } from "@/components/Pagination/Pagination";
import { getDownloads } from "@/lib/api/client";
import { getDictionary } from "@/lib/i18n/dictionary";
import { isSupportedLanguage } from "@/lib/i18n/languages";

interface DownloadsPageProps {
  params: Promise<{ lang: string }>;
  searchParams: Promise<{ page?: string }>;
}

export async function generateMetadata({
  params,
  searchParams,
}: DownloadsPageProps): Promise<Metadata> {
  const { lang } = await params;
  if (!isSupportedLanguage(lang)) return {};

  const { page: rawPage } = await searchParams;
  const page = parsePage(rawPage);

  // Wzorzec identyczny jak `posty/page.tsx` — self-referencing canonical per
  // stronę paginacji, hreflang tylko na stronie 1 (jedyna gwarantowana w
  // obu językach), endpoint listy nie zwraca meta pól (statyczne z dictionary).
  const dict = getDictionary(lang).downloads;
  const canonicalPath = page > 1 ? `/${lang}/do-pobrania?page=${page}` : `/${lang}/do-pobrania`;

  return {
    title: dict.metaTitle,
    description: dict.metaDescription,
    alternates: {
      canonical: canonicalPath,
      ...(page === 1
        ? {
            languages: {
              pl: "/pl/do-pobrania",
              en: "/en/do-pobrania",
              "x-default": "/pl/do-pobrania",
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

export default async function DownloadsPage({ params, searchParams }: DownloadsPageProps) {
  const { lang } = await params;
  if (!isSupportedLanguage(lang)) {
    notFound();
  }

  const { page: rawPage } = await searchParams;
  const page = parsePage(rawPage);

  // Strona 1 zawsze istnieje (pusta lista to poprawny stan, nie 404).
  // Strona poza zakresem paginacji → API zwraca 404 → `notFound()`.
  const result = await getDownloads(lang, page);
  if (!result) {
    notFound();
  }

  const dict = getDictionary(lang).downloads;

  return (
    <>
      <h1 className="page-title">{dict.heading}</h1>
      <DownloadList
        downloads={result.results}
        downloadLabel={dict.downloadLabel}
        downloadErrorMessage={dict.downloadError}
        emptyMessage={dict.empty}
      />
      <Pagination
        basePath={`/${lang}/do-pobrania`}
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
