import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { PostDetail } from "@/components/PostDetail/PostDetail";
import { getPost, getPosts } from "@/lib/api/client";
import { isSupportedLanguage, SUPPORTED_LANGUAGES } from "@/lib/i18n/languages";

interface PostPageProps {
  params: Promise<{ lang: string; slug: string }>;
}

/**
 * Statyczna lista sluggów per język w momencie builda — warunek dla
 * faktycznego SSG tej trasy (`.claude/rules/performance.md`), nie tylko
 * dla `/[lang]/o-mnie`. Posty opublikowane PO buildzie nadal działają:
 * `dynamicParams` domyślnie `true`, więc nieznany slug renderuje się
 * on-demand przy pierwszym żądaniu i jest cache'owany przez rewalidację
 * z `getPost` (15s) — ten sam mechanizm ISR, nie osobna ścieżka kodu.
 * Liczba postów w fazie 1 (pojedyncze cyfry) czyni pełną paginację przez
 * wszystkie strony tanią; przy realnym wzroście wolumenu do
 * przemyślenia osobno.
 */
export async function generateStaticParams() {
  const params: { lang: string; slug: string }[] = [];

  for (const lang of SUPPORTED_LANGUAGES) {
    let page = 1;
    for (;;) {
      const result = await getPosts(lang, page);
      if (!result) break;

      for (const post of result.results) {
        params.push({ lang, slug: post.slug });
      }

      if (!result.next) break;
      page += 1;
    }
  }

  return params;
}

export async function generateMetadata({ params }: PostPageProps): Promise<Metadata> {
  const { lang, slug } = await params;
  if (!isSupportedLanguage(lang)) return {};

  const post = await getPost(lang, slug);
  if (!post) return {};

  // Slug per wpis z `available_translations`, NIE bieżący slug strony —
  // każdy język ma własny slug.
  const languages: Record<string, string> = {};
  for (const translation of post.available_translations) {
    languages[translation.language] = `/${translation.language}/posty/${translation.slug}`;
  }
  const xDefault = languages.pl ?? Object.values(languages)[0];

  return {
    title: post.meta_title,
    description: post.meta_description,
    alternates: {
      canonical: `/${lang}/posty/${slug}`,
      languages: xDefault ? { ...languages, "x-default": xDefault } : languages,
    },
    openGraph: {
      type: "article",
      title: post.meta_title,
      description: post.meta_description,
      url: `/${lang}/posty/${slug}`,
      publishedTime: post.published_at ?? undefined,
      modifiedTime: post.updated_at,
      authors: [post.author],
      images: post.cover_image
        ? [{ url: post.cover_image, alt: post.cover_image_alt }]
        : undefined,
    },
    twitter: {
      card: "summary_large_image",
      title: post.meta_title,
      description: post.meta_description,
      images: post.cover_image ? [post.cover_image] : undefined,
    },
  };
}

export default async function PostPage({ params }: PostPageProps) {
  const { lang, slug } = await params;
  if (!isSupportedLanguage(lang)) {
    notFound();
  }

  // Nieistniejący slug ORAZ post nieopublikowany w tym języku → API zwraca
  // 404 → `notFound()`. Nie rozróżniamy tych dwóch przypadków dla widza —
  // oba oznaczają "nic tu nie ma po polsku/angielsku".
  const post = await getPost(lang, slug);
  if (!post) {
    notFound();
  }

  const siteUrl = process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000";
  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "BlogPosting",
    headline: post.title,
    datePublished: post.published_at ?? undefined,
    dateModified: post.updated_at,
    author: { "@type": "Person", name: post.author },
    image: post.cover_image ?? undefined,
    description: post.excerpt,
    mainEntityOfPage: `${siteUrl}/${lang}/posty/${slug}`,
  };

  return (
    <>
      {/* JSON-LD, nie HTML z CMS — serializujemy własny obiekt JS, bezpieczne. */}
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd).replace(/</g, "\\u003c") }}
      />
      <PostDetail post={post} lang={lang} />
    </>
  );
}
