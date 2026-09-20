/**
 * Typy odpowiedzi publicznego API (`/api/v1/{lang}/...`).
 *
 * Odzwierciedlają kontrakt zwracany przez `about.serializers` i
 * `blog.serializers` 1:1 — frontend nie zna szczegółów bazy, tylko ten
 * kontrakt (`.claude/rules/scope.md`: backend API-first).
 */

export interface Certificate {
  name: string;
  issuer: string;
  issued_year: number;
  image: string | null;
}

export interface AboutTranslationRef {
  language: string;
}

export interface About {
  full_name: string;
  headline: string;
  /** Sanityzowany HTML po stronie backendu — bezpieczny do `dangerouslySetInnerHTML`. */
  bio: string;
  photo: string | null;
  photo_alt: string;
  meta_title: string;
  meta_description: string;
  updated_at: string;
  available_translations: AboutTranslationRef[];
  certificates: Certificate[];
}

export interface PostSummary {
  slug: string;
  title: string;
  excerpt: string;
  cover_image: string | null;
  cover_image_alt: string;
  author: string;
  published_at: string | null;
}

export interface PostTranslationRef {
  language: string;
  slug: string;
}

export interface PostDetail extends PostSummary {
  /** Sanityzowany HTML po stronie backendu — bezpieczny do `dangerouslySetInnerHTML`. */
  content: string;
  meta_title: string;
  meta_description: string;
  updated_at: string;
  available_translations: PostTranslationRef[];
}

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}
