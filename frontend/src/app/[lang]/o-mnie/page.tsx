import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { AboutSection } from "@/components/AboutSection/AboutSection";
import { getAbout } from "@/lib/api/client";
import { isSupportedLanguage } from "@/lib/i18n/languages";

interface AboutPageProps {
  params: Promise<{ lang: string }>;
}

export async function generateMetadata({ params }: AboutPageProps): Promise<Metadata> {
  const { lang } = await params;
  if (!isSupportedLanguage(lang)) return {};

  const about = await getAbout(lang);
  if (!about) return {};

  // Tylko opublikowane wersje (już przefiltrowane przez API) — singleton
  // „O mnie" nie ma własnego sluga, więc adres jest zawsze `/{lang}/o-mnie`.
  const languages: Record<string, string> = {};
  for (const translation of about.available_translations) {
    languages[translation.language] = `/${translation.language}/o-mnie`;
  }
  const xDefault = languages.pl ?? Object.values(languages)[0];

  return {
    title: about.meta_title,
    description: about.meta_description,
    alternates: {
      canonical: `/${lang}/o-mnie`,
      languages: xDefault ? { ...languages, "x-default": xDefault } : languages,
    },
    openGraph: {
      type: "profile",
      title: about.meta_title,
      description: about.meta_description,
      url: `/${lang}/o-mnie`,
      images: about.photo ? [{ url: about.photo, alt: about.photo_alt }] : undefined,
    },
    twitter: {
      card: "summary_large_image",
      title: about.meta_title,
      description: about.meta_description,
      images: about.photo ? [about.photo] : undefined,
    },
  };
}

export default async function AboutPage({ params }: AboutPageProps) {
  const { lang } = await params;
  if (!isSupportedLanguage(lang)) {
    notFound();
  }

  // Brak tłumaczenia w tym języku (nieopublikowane albo nie istnieje) → 404,
  // tak samo jak nieistniejący slug posta.
  const about = await getAbout(lang);
  if (!about) {
    notFound();
  }

  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "ProfilePage",
    mainEntity: {
      "@type": "Person",
      name: about.full_name,
      jobTitle: about.headline,
      image: about.photo ?? undefined,
      description: stripHtml(about.bio),
    },
  };

  return (
    <>
      {/* JSON-LD, nie HTML z CMS — serializujemy własny obiekt JS, bezpieczne. */}
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd).replace(/</g, "\\u003c") }}
      />
      <AboutSection about={about} lang={lang} />
    </>
  );
}

function stripHtml(html: string): string {
  return html
    .replace(/<[^>]+>/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}
