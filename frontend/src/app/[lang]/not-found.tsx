import Link from "next/link";
import { headers } from "next/headers";

import { getDictionary } from "@/lib/i18n/dictionary";
import { isSupportedLanguage } from "@/lib/i18n/languages";

/**
 * Server Component — trafiają tu zarówno nieistniejące sluggi/strony pod
 * poprawnym `[lang]`, jak i sam nieobsługiwany `[lang]` (layout woła
 * `notFound()` przed walidacją). `not-found.tsx` nie dostaje `params`
 * (konwencja Next.js), więc język czytamy z nagłówka `x-lang`
 * wstrzykniętego przez `proxy.ts` — dla nieobsługiwanego `[lang]` to
 * zawsze `pl` (middleware sam waliduje przed wstawieniem nagłówka), więc
 * fallback poniżej dotyczy tylko naprawdę brakującego nagłówka.
 */
export default async function LangNotFound() {
  const headerList = await headers();
  const rawLang = headerList.get("x-lang") ?? "";
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
