import "server-only";

/**
 * Przepisz absolutny URL obrazu z API (zbudowany z publicznego `SITE_URL`
 * backendu — potrzebny dla `og:image`/`twitter:image`/JSON-LD) na adres
 * osiągalny z *tego* procesu serwera, pod optymalizację `next/image`.
 *
 * W Dockerze `SITE_URL` to adres widoczny dla przeglądarki/crawlera
 * (`http://localhost:8000`) — nieosiągalny z wnętrza kontenera frontendu,
 * gdzie „localhost” to sam ten kontener. `API_URL` to adres osiągalny w
 * sieci compose (`http://backend:8000`). Poza Dockerem oba wskazują na ten
 * sam host, więc to wtedy no-op.
 *
 * Używaj WYŁĄCZNIE dla `<Image src>` — nigdy dla `og:image`/`twitter:image`/
 * JSON-LD, które muszą zostać publicznie osiągalne.
 */
export function toOptimizableImageSrc(url: string): string {
  const internalBase = process.env.API_URL;
  if (!internalBase) return url;

  try {
    const internal = new URL(internalBase);
    const target = new URL(url);
    target.protocol = internal.protocol;
    target.host = internal.host;
    return target.toString();
  } catch {
    return url;
  }
}
