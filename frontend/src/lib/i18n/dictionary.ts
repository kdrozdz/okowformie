import type { Language } from "./languages";

/**
 * Statyczne teksty UI (nawigacja, etykiety, stany pustki/błędu) — nie
 * pochodzą z API, bo dotyczą szkieletu strony, nie treści redakcyjnej.
 * Treść redakcyjna (posty, „O mnie") zawsze z API, nigdy stąd.
 */
export interface Dictionary {
  header: {
    homeAriaLabel: string;
    linkedinAriaLabel: string;
    instagramAriaLabel: string;
    facebookAriaLabel: string;
    navAriaLabel: string;
    navAbout: string;
    navPosts: string;
    navDownloads: string;
  };
  footer: {
    tagline: string;
    copyright: string;
  };
  posts: {
    heading: string;
    metaTitle: string;
    metaDescription: string;
    empty: string;
    previousPage: string;
    nextPage: string;
    paginationAriaLabel: string;
  };
  postDetail: {
    back: string;
  };
  downloads: {
    heading: string;
    metaTitle: string;
    metaDescription: string;
    empty: string;
    downloadLabel: string;
    downloadError: string;
    previousPage: string;
    nextPage: string;
    paginationAriaLabel: string;
  };
  certificates: {
    heading: string;
    countLabel: string;
    prevAriaLabel: string;
    nextAriaLabel: string;
    lightboxCloseAriaLabel: string;
    lightboxPrevAriaLabel: string;
    lightboxNextAriaLabel: string;
    lightboxDialogAriaLabel: string;
  };
  error: {
    heading: string;
    message: string;
    retry: string;
  };
  notFound: {
    heading: string;
    message: string;
    backHome: string;
  };
}

const DICTIONARIES: Record<Language, Dictionary> = {
  pl: {
    header: {
      homeAriaLabel: "okowFormie — strona główna",
      linkedinAriaLabel: "okowFormie na LinkedIn",
      instagramAriaLabel: "okowFormie na Instagramie",
      facebookAriaLabel: "okowFormie na Facebooku",
      navAriaLabel: "Sekcje strony",
      navAbout: "O mnie",
      navPosts: "Posty",
      navDownloads: "Do pobrania",
    },
    footer: {
      tagline: "Blog o zdrowiu wzroku, terapii widzenia i optometrii.",
      copyright: "© 2026 okowFormie. Wszelkie prawa zastrzeżone.",
    },
    posts: {
      heading: "Najnowsze wpisy",
      metaTitle: "Blog | okowFormie",
      metaDescription:
        "Praktyczne artykuły o zdrowiu wzroku, doborze soczewek kontaktowych, okularach i optometrii — porady napisane przez optometrystkę, bez branżowego żargonu.",
      empty: "Brak opublikowanych wpisów.",
      previousPage: "Poprzednia strona",
      nextPage: "Następna strona",
      paginationAriaLabel: "Stronicowanie",
    },
    postDetail: {
      back: "Wróć do listy",
    },
    downloads: {
      heading: "Do pobrania",
      metaTitle: "Do pobrania | okowFormie",
      metaDescription:
        "Materiały do pobrania — ulotki, ćwiczenia i poradniki o zdrowiu wzroku w formacie PDF.",
      empty: "Brak plików do pobrania.",
      downloadLabel: "Pobierz plik",
      downloadError: "Nie udało się pobrać pliku. Plik otworzył się w nowej karcie — spróbuj pobrać go stamtąd.",
      previousPage: "Poprzednia strona",
      nextPage: "Następna strona",
      paginationAriaLabel: "Stronicowanie",
    },
    certificates: {
      heading: "Moje kursy, szkolenia, certyfikaty",
      countLabel: "łącznie",
      prevAriaLabel: "Przewiń w lewo",
      nextAriaLabel: "Przewiń w prawo",
      lightboxCloseAriaLabel: "Zamknij",
      lightboxPrevAriaLabel: "Poprzedni certyfikat",
      lightboxNextAriaLabel: "Następny certyfikat",
      lightboxDialogAriaLabel: "Podgląd certyfikatu",
    },
    error: {
      heading: "Coś poszło nie tak",
      message: "Nie udało się pobrać danych. Spróbuj ponownie za chwilę.",
      retry: "Spróbuj ponownie",
    },
    notFound: {
      heading: "Nie znaleziono strony",
      message: "Treść, której szukasz, nie istnieje albo nie została jeszcze opublikowana.",
      backHome: "Wróć do strony O mnie",
    },
  },
  en: {
    header: {
      homeAriaLabel: "okowFormie — home",
      linkedinAriaLabel: "okowFormie on LinkedIn",
      instagramAriaLabel: "okowFormie on Instagram",
      facebookAriaLabel: "okowFormie on Facebook",
      navAriaLabel: "Site sections",
      navAbout: "About",
      navPosts: "Posts",
      navDownloads: "Downloads",
    },
    footer: {
      tagline: "A blog about eye health, vision therapy and optometry.",
      copyright: "© 2026 okowFormie. All rights reserved.",
    },
    posts: {
      heading: "Latest posts",
      metaTitle: "Blog | okowFormie",
      metaDescription:
        "Practical articles about eye health, choosing contact lenses, glasses and optometry — written by a working optometrist, no jargon, just what actually helps.",
      empty: "No published posts yet.",
      previousPage: "Previous page",
      nextPage: "Next page",
      paginationAriaLabel: "Pagination",
    },
    postDetail: {
      back: "Back to the list",
    },
    downloads: {
      heading: "Downloads",
      metaTitle: "Downloads | okowFormie",
      metaDescription:
        "Downloadable materials — leaflets, exercises and guides about eye health in PDF format.",
      empty: "No downloads available yet.",
      downloadLabel: "Download file",
      downloadError: "The file couldn't be downloaded. It opened in a new tab instead — try downloading it from there.",
      previousPage: "Previous page",
      nextPage: "Next page",
      paginationAriaLabel: "Pagination",
    },
    certificates: {
      heading: "My courses, training and certificates",
      countLabel: "total",
      prevAriaLabel: "Scroll left",
      nextAriaLabel: "Scroll right",
      lightboxCloseAriaLabel: "Close",
      lightboxPrevAriaLabel: "Previous certificate",
      lightboxNextAriaLabel: "Next certificate",
      lightboxDialogAriaLabel: "Certificate preview",
    },
    error: {
      heading: "Something went wrong",
      message: "We couldn't load the data. Please try again in a moment.",
      retry: "Try again",
    },
    notFound: {
      heading: "Page not found",
      message: "The content you're looking for doesn't exist or hasn't been published yet.",
      backHome: "Back to the About page",
    },
  },
};

export function getDictionary(lang: Language): Dictionary {
  return DICTIONARIES[lang];
}
