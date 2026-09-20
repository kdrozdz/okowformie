import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { Karla, Sora } from "next/font/google";

import "../globals.css";

import { Footer } from "@/components/Footer/Footer";
import { Header } from "@/components/Header/Header";
import { getAbout, getBranding } from "@/lib/api/client";
import type { Branding } from "@/lib/api/types";
import { isSupportedLanguage, SUPPORTED_LANGUAGES, type Language } from "@/lib/i18n/languages";

const sora = Sora({
  subsets: ["latin", "latin-ext"],
  weight: ["500", "600", "700"],
  variable: "--font-sora",
  display: "swap",
});

const karla = Karla({
  subsets: ["latin", "latin-ext"],
  weight: ["400", "500"],
  variable: "--font-karla",
  display: "swap",
});

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000";

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
};

export function generateStaticParams() {
  return SUPPORTED_LANGUAGES.map((lang) => ({ lang }));
}

/**
 * Prawdziwy root layout (`<html>`/`<body>` żyją tu, nie w `app/layout.tsx`
 * — ten plik nie istnieje). Możliwe dopiero teraz: `/` jest w całości
 * obsługiwane przez `proxy.ts` (redirect na `/${DEFAULT_LANG}` zanim Next.js
 * spróbuje dopasować trasę), więc nie ma już żadnego `page.tsx` bezpośrednio
 * pod `app/` — `[lang]/layout.tsx` jest jedynym layoutem nad wszystkimi
 * stronami i może być root layoutem, biorąc `lang` ze STATYCZNEGO segmentu
 * `params` zamiast z `headers()`. To eliminuje jedyne użycie Dynamic API
 * w drzewie layoutów, które wcześniej opt-outowało całą appkę z SSG/ISR
 * (`.claude/rules/performance.md`) — zweryfikowane realnym `next build`,
 * patrz `docs/tasks/10-live-frontend-nextjs.md`.
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
  const [about, branding] = await Promise.all([getAboutSafely(lang), getBrandingSafely()]);

  return (
    <html lang={lang} className={`${sora.variable} ${karla.variable}`}>
      {/* Rozszerzenia przeglądarki (np. ColorZilla) dopisują własne atrybuty
          do <body> (np. `cz-shortcut-listen`) zanim React się zhydratuje —
          znany, nieszkodliwy fałszywy alarm hydratacji, udokumentowany
          wprost przez Next.js/React jako powód do `suppressHydrationWarning`
          na tym konkretnym węźle. Ogranicza się do atrybutów <body>, nie
          wycisza prawdziwych niezgodności hydratacji w dzieciach poniżej. */}
      <body suppressHydrationWarning>
        <Header lang={lang as Language} authorName={about?.full_name ?? null} branding={branding} />
        <main className="page-content">{children}</main>
        <Footer lang={lang as Language} branding={branding} />
      </body>
    </html>
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

async function getBrandingSafely(): Promise<Branding | null> {
  try {
    return await getBranding();
  } catch (error) {
    // Analogicznie do `getAboutSafely` — logo/social linki niedostępne to
    // degradacja (fallback na statyczne `public/brand/logo.png`, brak ikon social
    // w headerze), nie błąd krytyczny wywracający całą witrynę.
    console.error("Nie udało się pobrać danych brandingu dla headera:", error);
    return null;
  }
}
