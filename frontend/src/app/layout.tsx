import type { Metadata } from "next";
import { headers } from "next/headers";
import { Karla, Sora } from "next/font/google";

import "./globals.css";

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

/**
 * Jedyny prawdziwy root layout — MUSI leżeć dokładnie w `app/` (Next.js
 * wymaga, żeby każdy `page.tsx`, łącznie z tymi poza `[lang]`, miał jakiś
 * root layout nad sobą; inaczej `next build` pada, zweryfikowane empirycznie
 * w tym repo na Next.js 16.3.5 zarówno pod Turbopackiem, jak i webpackiem).
 *
 * To wyklucza użycie `next/root-params` do dynamicznego `<html lang>` —
 * ten mechanizm działa tylko, gdy `[lang]/layout.tsx` SAM jest root
 * layoutem (`[lang]` musi leżeć „przed" nim), a tu root layout leży wyżej.
 * Zamiast tego `proxy.ts` wstrzykuje nagłówek `x-lang` na podstawie
 * pierwszego segmentu URL, czytany tu przez `headers()` — atrybut
 * pozostaje naprawdę dynamiczny (`.claude/rules/seo.md`), inną drogą niż
 * pierwotnie próbowana.
 */
export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const headerList = await headers();
  const lang = headerList.get("x-lang") ?? "pl";

  return (
    <html lang={lang} className={`${sora.variable} ${karla.variable}`}>
      <body>{children}</body>
    </html>
  );
}
