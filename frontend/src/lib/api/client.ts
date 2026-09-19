import "server-only";

import type { Language } from "@/lib/i18n/languages";

import type { About, PaginatedResponse, PostDetail, PostSummary } from "./types";

/**
 * Fetch wyłącznie server-side (Server Components, `generateMetadata`,
 * `generateStaticParams`) — stąd `import "server-only"` powyżej, żeby
 * przypadkowy import w kliencie wywalił build zamiast wyciekać nieużywalny
 * tam adres kontenera.
 *
 * `API_URL` (bez `NEXT_PUBLIC_`) rozwiązuje się w sieci compose do
 * `http://backend:8000`; fallback na `NEXT_PUBLIC_API_URL` obsługuje gołe
 * `npm run dev` bez compose, gdzie oba warianty wskazują na ten sam host.
 */
function getApiBaseUrl(): string {
  return process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
}

// Rewalidacja czasowa zamiast SSR na każde żądanie — webhook publikacji z
// panelu redakcyjnego nie istnieje jeszcze (`.claude/rules/performance.md`
// dopuszcza obie strategie; webhook to osobny task, gdy panel tego
// potrzebuje). 60s to rozsądny kompromis świeżość/obciążenie API dla bloga
// aktualizowanego kilka razy w tygodniu, nie w czasie rzeczywistym.
const REVALIDATE_SECONDS = 60;

/**
 * `null` = zasób nie istnieje (404) — wywołujący decyduje, czy to `notFound()`
 * czy pusty stan. Każdy inny błąd (sieć, 5xx) rzuca wyjątek, który łapie
 * najbliższy `error.tsx` (`app/[lang]/error.tsx`) — spójny sposób
 * sygnalizowania „błędu pobrania danych" w całej aplikacji, nie
 * try/catch per strona.
 */
async function fetchApi<T>(path: string): Promise<T | null> {
  const url = `${getApiBaseUrl()}${path}`;
  let response: Response;
  try {
    response = await fetch(url, { next: { revalidate: REVALIDATE_SECONDS } });
  } catch (cause) {
    throw new Error(`Nie udało się połączyć z API: ${url}`, { cause });
  }

  if (response.status === 404) {
    return null;
  }
  if (!response.ok) {
    throw new Error(`API zwróciło błąd ${response.status} ${response.statusText}: ${url}`);
  }
  return (await response.json()) as T;
}

export function getAbout(lang: Language): Promise<About | null> {
  return fetchApi<About>(`/api/v1/${lang}/about/`);
}

export function getPosts(
  lang: Language,
  page: number,
): Promise<PaginatedResponse<PostSummary> | null> {
  return fetchApi<PaginatedResponse<PostSummary>>(`/api/v1/${lang}/posts/?page=${page}`);
}

export function getPost(lang: Language, slug: string): Promise<PostDetail | null> {
  return fetchApi<PostDetail>(`/api/v1/${lang}/posts/${encodeURIComponent(slug)}/`);
}
