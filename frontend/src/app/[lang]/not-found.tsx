"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { getDictionary } from "@/lib/i18n/dictionary";
import { isSupportedLanguage } from "@/lib/i18n/languages";

/**
 * Trafiają tu zarówno nieistniejące sluggi/strony pod poprawnym `[lang]`,
 * jak i sam nieobsługiwany `[lang]` (layout woła `notFound()` przed
 * walidacją). `not-found.tsx` nie dostaje `params` (konwencja Next.js) —
 * tak samo jak `error.tsx` obok, Client Component czytający pierwszy
 * segment z `usePathname()` zamiast Dynamic API (`headers()`). To
 * ostatnie, poza layoutem, miejsce w drzewie `[lang]`, które używało
 * `headers()` — jego usunięcie było konieczne, żeby `[lang]/layout.tsx`
 * (teraz root layout) mogło faktycznie renderować się statycznie: Next.js
 * traktuje `not-found.tsx` jako część tego samego segmentu co layout, więc
 * Dynamic API użyte w nim opt-outowało cały segment z SSG, mimo że sam
 * layout już go nie wołał (zweryfikowane empirycznie realnym `next build`
 * — trasy wracały jako `ƒ`/dynamiczne, dopóki to nie zostało poprawione).
 */
export default function LangNotFound() {
  const pathname = usePathname();
  const rawLang = pathname.split("/")[1] ?? "";
  const lang = isSupportedLanguage(rawLang) ? rawLang : "pl";
  const dict = getDictionary(lang).notFound;

  return (
    <div>
      <h1 className="page-title">{dict.heading}</h1>
      <p>{dict.message}</p>
      <Link href={`/${lang}/o-mnie`}>{dict.backHome}</Link>
    </div>
  );
}
