import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

import { isSupportedLanguage } from "@/lib/i18n/languages";

const LANG_HEADER = "x-lang";
const DEFAULT_LANG = "pl";

/**
 * Dwie role:
 * 1. `/` → `/{DEFAULT_LANG}`, 307 (nie 308 — domyślny język może się
 *    kiedyś zmienić, to nie jest trwałe przekierowanie).
 * 2. Wstrzykuje nagłówek `x-lang` (pierwszy segment ścieżki, jeśli to
 *    wspierany język) — jedyny sposób, żeby `app/layout.tsx` (root layout,
 *    MUSI siedzieć dokładnie w `app/`, patrz jego doc-komentarz) znał
 *    język do `<html lang>`, skoro sam nie ma dostępu do `params` segmentu
 *    `[lang]` leżącego niżej w drzewie tras.
 */
export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;

  if (pathname === "/") {
    return NextResponse.redirect(new URL(`/${DEFAULT_LANG}`, request.url), 307);
  }

  const firstSegment = pathname.split("/")[1] ?? "";
  const lang = isSupportedLanguage(firstSegment) ? firstSegment : DEFAULT_LANG;

  const requestHeaders = new Headers(request.headers);
  requestHeaders.set(LANG_HEADER, lang);

  return NextResponse.next({ request: { headers: requestHeaders } });
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
