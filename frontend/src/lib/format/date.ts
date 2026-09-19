import type { Language } from "@/lib/i18n/languages";

const LOCALE_BY_LANGUAGE: Record<Language, string> = {
  pl: "pl-PL",
  en: "en-US",
};

/** Data w formacie długim ("12 września 2026" / "September 12, 2026"). */
export function formatDate(iso: string, lang: Language): string {
  return new Intl.DateTimeFormat(LOCALE_BY_LANGUAGE[lang], {
    day: "numeric",
    month: "long",
    year: "numeric",
  }).format(new Date(iso));
}
