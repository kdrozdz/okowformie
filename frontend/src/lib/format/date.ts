import type { Language } from "@/lib/i18n/languages";

const LOCALE_BY_LANGUAGE: Record<Language, string> = {
  pl: "pl-PL",
  en: "en-US",
};

/**
 * Data w formacie długim ("12 września 2026" / "September 12, 2026").
 *
 * `timeZone` ustawiony jawnie (nie domyślna strefa środowiska uruchomienia):
 * bez tego serwer (zwykle UTC w kontenerze) i przeglądarka użytkownika (inna
 * strefa) mogą sformatować tę samą datę na inny dzień kalendarzowy blisko
 * północy UTC — różny tekst między SSR a hydratacją klienta psuje całą
 * hydratację strony (React porównuje tekst również w drzewie renderowanym
 * przez Server Components, nie tylko w komponentach klienckich).
 */
export function formatDate(iso: string, lang: Language): string {
  return new Intl.DateTimeFormat(LOCALE_BY_LANGUAGE[lang], {
    day: "numeric",
    month: "long",
    year: "numeric",
    timeZone: "Europe/Warsaw",
  }).format(new Date(iso));
}
