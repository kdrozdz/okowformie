import { notFound } from "next/navigation";

import { Footer } from "@/components/Footer/Footer";
import { Header } from "@/components/Header/Header";
import { getAbout } from "@/lib/api/client";
import { isSupportedLanguage, SUPPORTED_LANGUAGES, type Language } from "@/lib/i18n/languages";

export function generateStaticParams() {
  return SUPPORTED_LANGUAGES.map((lang) => ({ lang }));
}

/**
 * Nested layout (NIE root — `<html>`/`<body>` żyją w `app/layout.tsx`,
 * patrz jego doc-komentarz). Waliduje `[lang]` i renderuje wspólny
 * szkielet (Header/Footer) dla `/o-mnie`, `/posty`, `/posty/[slug]`.
 */
export default async function LangLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ lang: string }>;
}) {
  const { lang } = await params;
  if (!isSupportedLanguage(lang)) {
    notFound();
  }

  const about = await getAboutSafely(lang);

  return (
    <>
      <Header lang={lang} authorName={about?.full_name ?? null} />
      <main className="page-content">{children}</main>
      <Footer lang={lang} />
    </>
  );
}

async function getAboutSafely(lang: Language) {
  try {
    return await getAbout(lang);
  } catch (error) {
    // Nagłówek nie może wywrócić całej witryny, gdy tylko endpoint „O mnie”
    // ma przejściowy problem — brak nazwiska w headerze to degradacja, nie
    // błąd krytyczny. Strona /o-mnie sama zgłosi błąd przez `error.tsx`.
    console.error("Nie udało się pobrać danych „O mnie” dla headera:", error);
    return null;
  }
}
