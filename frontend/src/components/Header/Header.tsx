import Image from "next/image";
import Link from "next/link";

import type { Branding } from "@/lib/api/types";
import { getDictionary } from "@/lib/i18n/dictionary";
import type { Language } from "@/lib/i18n/languages";
import { toOptimizableImageSrc } from "@/lib/media/image-src";

import { getSocialIconRegistry } from "./icons";
import { PrimaryNav } from "./PrimaryNav";
import styles from "./Header.module.css";

interface HeaderProps {
  lang: Language;
  /** `about.full_name`, gdy dostępne — brak (np. tłumaczenie niepublikowane) nie blokuje renderu headera. */
  authorName: string | null;
  /**
   * `null` = wyłącznie błąd pobrania danych z API (`getBranding()` zawsze
   * rzuca zamiast zwracać `null` dla tego endpointu — patrz `lib/api/client.ts`) —
   * fallback na statyczne `public/brand/logo.png`, bez linków social. Panel
   * jeszcze nieskonfigurowany to NIE `null`, tylko realny obiekt
   * `{ logo: null, social_links: [] }`.
   */
  branding: Branding | null;
}

export function Header({ lang, authorName, branding }: HeaderProps) {
  const dict = getDictionary(lang).header;
  const socialIconRegistry = getSocialIconRegistry(dict);
  // Platforma z API spoza zamkniętego rejestru (nie powinna wystąpić przy
  // obecnym backendzie — `SocialPlatform` to te same trzy wartości — ale
  // bądź defensywny) jest pomijana w renderze, nie wywraca strony.
  const socialLinks = (branding?.social_links ?? []).filter(
    (link) => socialIconRegistry[link.platform] !== undefined,
  );
  const logoSrc = branding?.logo ? toOptimizableImageSrc(branding.logo) : "/brand/logo.png";

  return (
    <header className={styles.siteHeader}>
      <div className={styles.brandBlock}>
        <div className={styles.brandLogoCol}>
          {/* Cel bezpośredni (nie `/${lang}`), żeby uniknąć widocznego
              mignięcia treści: `/${lang}` to sam server-side redirect do
              `/${lang}/o-mnie` (`app/[lang]/page.tsx`) — kliknięcie w niego
              wymuszałoby dodatkowy przeskok zamiast płynnej nawigacji
              klienckiej, jaką ma "O mnie" w `PrimaryNav`. */}
          <Link
            className={styles.brandLogoLink}
            href={`/${lang}/o-mnie`}
            aria-label={dict.homeAriaLabel}
          >
            <Image
              className={styles.brandMark}
              src={logoSrc}
              alt=""
              width={80}
              height={80}
            />
          </Link>
          {socialLinks.length > 0 ? (
            <div className={styles.brandSocial}>
              {socialLinks.map((link) => {
                const { className, ariaLabel, Icon } = socialIconRegistry[link.platform];
                return (
                  <a
                    key={link.platform}
                    className={className}
                    href={link.url}
                    aria-label={ariaLabel}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    <Icon />
                  </a>
                );
              })}
            </div>
          ) : null}
        </div>
      </div>

      {/* Wordmark — celowo NIE <h1> (mockup: `.site-title`), H1 należy do treści strony. */}
      <p className={styles.siteTitle}>
        <span className={styles.siteTitleName}>
          <span className={styles.siteTitleNameTeal}>Oko</span>{" "}
          <span className={styles.siteTitleNameNavy}>w</span>{" "}
          <span className={styles.siteTitleNameIndigo}>Formie</span>
        </span>
        {authorName ? <span className={styles.siteTitleAuthor}>{authorName}</span> : null}
      </p>

      <PrimaryNav
        lang={lang}
        ariaLabel={dict.navAriaLabel}
        aboutLabel={dict.navAbout}
        postsLabel={dict.navPosts}
        downloadsLabel={dict.navDownloads}
      />
    </header>
  );
}
