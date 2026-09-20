import { readFile } from "node:fs/promises";
import { join } from "node:path";

import { getBranding } from "@/lib/api/client";
import { toOptimizableImageSrc } from "@/lib/media/image-src";

/**
 * Route dynamiczny (`icon.tsx`), nie statyczny plik `icon.png` — favicon musi
 * odzwierciedlać logo wgrane w panelu (`branding.SiteBranding`, ten sam
 * branding co `Header`/`Footer`), nie zahardkodowany asset z buildu. Fetch
 * do API poniżej daje Next.js sygnał, żeby wykonywać tę funkcję ponownie
 * zgodnie z jej cache'owaniem (`revalidate`), zamiast statycznie optymalizować
 * raz na build tak, jak dzieje się to bez żadnego zewnętrznego fetcha.
 */
export const size = { width: 32, height: 32 };

// Redaktor wgrywa PNG/JPG/WebP (`core.validators.validate_image_upload`
// dopuszcza wszystkie trzy) — brak statycznego eksportu `contentType`
// jest celowy: Next.js czyta faktyczny `Content-Type` z odpowiedzi zwróconej
// przez ten route (patrz `Content-Type` ustawiony niżej z realnej odpowiedzi
// backendu/fallbacku), więc zadeklarowanie tu jednego typu na stałe
// wprowadzałoby rozjazd dla logo w formacie innym niż PNG. Zweryfikowane
// przez `curl -sI http://localhost:3000/icon` — patrz raport w PR/tasku.
export default async function Icon() {
  try {
    const branding = await getBranding();

    if (branding.logo) {
      // `branding.logo` jest URL-em publicznym (`SITE_URL`, widocznym dla
      // przeglądarki) — ta funkcja jednak fetchuje server-side, wewnątrz
      // kontenera frontendu, gdzie ten host bywa nieosiągalny (patrz
      // `toOptimizableImageSrc` w `lib/media/image-src.ts`, ten sam problem
      // co `next/image` dla `about.photo`).
      const response = await fetch(toOptimizableImageSrc(branding.logo), {
        next: { revalidate: 15 },
      });
      if (response.ok) {
        const contentType = response.headers.get("content-type") ?? "image/png";
        return new Response(await response.arrayBuffer(), {
          headers: { "Content-Type": contentType },
        });
      }
    }
  } catch (error) {
    // Analogicznie do `getBrandingSafely` w `[lang]/layout.tsx` — błąd API
    // (backend nieosiągalny, błąd sieci) albo błąd samego fetcha obrazu nie
    // może wywrócić trasy `/icon`; obie ścieżki błędu spadają do tego
    // samego statycznego fallbacku niżej.
    console.error("Nie udało się pobrać logo z brandingu dla favicony:", error);
  }

  // Fallback: ten sam statyczny plik co Header/Footer, gdy branding
  // niedostępny (błąd API), logo jeszcze nie wgrane w panelu, albo
  // odpowiedź z drugiego fetcha nie jest `ok`.
  const fallback = await readFile(join(process.cwd(), "public/brand/logo.png"));
  return new Response(new Uint8Array(fallback), {
    headers: { "Content-Type": "image/png" },
  });
}
