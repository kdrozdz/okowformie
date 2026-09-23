//: Znaki polskie, które nie mają dekompozycji NFKD (to osobne litery, nie
//: kombinacje diakrytyczne, więc `String.prototype.normalize` sam ich nie
//: rozbija) — muszą być zmapowane jawnie. Ograniczone do PL/EN — jedynych
//: dwóch języków serwisu (`scope.md`) — bez uogólniania pod pismo, którego
//: strona nigdy nie pokazuje.
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
 * Ostatni segment ścieżki z URL-a pliku — czyli faktyczna, losowa nazwa
 * nadana przez `core.storage.RandomFilenameUploadTo` na storage (np.
 * `a3f9c1b2d4e5....pdf`). Operacje wyłącznie na stringu (bez `new URL()`):
 * `fileUrl` z kontraktu API jest zawsze absolutne, ale ta funkcja nie ma się
 * wywalić na relatywnej/zdeformowanej wartości, gdyby `SITE_URL` było kiedyś
 * źle skonfigurowane po stronie backendu (`core.api.absolute_media_url`) —
 * zepsuta konfiguracja ma dać zepsuty link, nie 500 na całej stronie.
 */
function originalFilename(fileUrl: string): string {
  const withoutQuery = fileUrl.split(/[?#]/, 1)[0];
  const segments = withoutQuery.split("/");
  return segments[segments.length - 1] || "plik";
}

/**
 * Czytelna nazwa pliku do atrybutu `download` — bez tego przeglądarka
 * podstawia nazwę wprost z URL-a, czyli losowy UUID ze storage (celowa
 * decyzja bezpieczeństwa dla nazwy *na storage*, `.claude/rules/security.md`,
 * ale zły UX dla pliku, który użytkownik faktycznie zapisuje na dysku).
 *
 * Rozszerzenie brane z rzeczywistej nazwy pliku (nie zakładane na sztywno,
 * dziś zawsze `.pdf` — `downloads.validators.validate_pdf_upload` gwarantuje
 * to po stronie backendu, ale ta funkcja nie zakłada tego wprost). Gdy tytuł
 * nie da się sprowadzić do żadnego znaku alfanumerycznego (np. sam
 * interpunkcja/emoji), zamiast kolizyjnej stałej ("plik.pdf" dla każdego
 * takiego wpisu) wraca oryginalna nazwa ze storage — losowa, ale unikalna.
 */
export function downloadFilename(title: string, fileUrl: string): string {
  const original = originalFilename(fileUrl);
  const extensionMatch = /\.[a-z0-9]+$/i.exec(original);
  const extension = extensionMatch ? extensionMatch[0].toLowerCase() : "";

  const withoutPolishChars = title
    .toLowerCase()
    .replace(/[ąćęłńóśźż]/g, (char) => POLISH_CHAR_MAP[char] ?? char);

  const slug = withoutPolishChars.replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "");

  return slug ? `${slug}${extension}` : original;
}
