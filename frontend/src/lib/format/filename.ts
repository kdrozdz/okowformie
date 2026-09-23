//: Znaki polskie, które NFKD nie rozkłada na literę + akcent (to osobne
//: litery, nie kombinacje diakrytyczne) — muszą być zmapowane jawnie przed
//: resztą normalizacji.
const POLISH_CHAR_MAP: Record<string, string> = {
  ą: "a",
  ć: "c",
  ę: "e",
  ł: "l",
  ń: "n",
  ó: "o",
  ś: "s",
  ź: "z",
  ż: "z",
};

/**
 * Czytelna nazwa pliku do atrybutu `download` — bez tego przeglądarka
 * podstawia nazwę wprost z URL-a, czyli losowy UUID wygenerowany przez
 * `core.storage.RandomFilenameUploadTo` (celowa decyzja bezpieczeństwa dla
 * nazwy na storage, `.claude/rules/security.md`, ale zły UX dla pliku, który
 * użytkownik faktycznie zapisuje na dysku).
 *
 * Rozszerzenie brane z rzeczywistego URL-a pliku, nie zakładane na sztywno —
 * dziś `downloads` dopuszcza tylko PDF, ale funkcja nie ma się zepsuć, gdyby
 * to się kiedyś zmieniło.
 */
export function downloadFilename(title: string, fileUrl: string): string {
  const extensionMatch = /\.[a-z0-9]+$/i.exec(new URL(fileUrl).pathname);
  const extension = extensionMatch ? extensionMatch[0].toLowerCase() : "";

  const withoutPolishChars = title
    .toLowerCase()
    .replace(/[ąćęłńóśźż]/g, (char) => POLISH_CHAR_MAP[char] ?? char);

  const slug = withoutPolishChars
    .normalize("NFKD")
    .replace(/[̀-ͯ]/g, "")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");

  return `${slug || "plik"}${extension}`;
}
