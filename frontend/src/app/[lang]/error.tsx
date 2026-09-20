"use client";

import { useEffect } from "react";
import { usePathname } from "next/navigation";

import { getDictionary } from "@/lib/i18n/dictionary";
import { isSupportedLanguage } from "@/lib/i18n/languages";

/**
 * `error.tsx` musi być Client Component (wymóg Next.js) — nie może więc
 * użyć `next/root-params`. Język czytamy z pierwszego segmentu ścieżki
 * (`usePathname()`), z fallbackiem na `pl`, tylko dla tekstu TEGO
 * komunikatu — reset nadal wróci do faktycznie żądanej strony.
 */
export default function LangError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  const pathname = usePathname();
  const rawLang = pathname.split("/")[1] ?? "";
  const lang = isSupportedLanguage(rawLang) ? rawLang : "pl";
  const dict = getDictionary(lang).error;

  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div role="alert">
      <h1 className="page-title">{dict.heading}</h1>
      <p>{dict.message}</p>
      <button type="button" onClick={() => reset()}>
        {dict.retry}
      </button>
    </div>
  );
}
