import Image from "next/image";
import Link from "next/link";

import { getDictionary } from "@/lib/i18n/dictionary";
import type { Language } from "@/lib/i18n/languages";

import { PrimaryNav } from "./PrimaryNav";
import styles from "./Header.module.css";

interface HeaderProps {
  lang: Language;
  /** `about.full_name`, gdy dostępne — brak (np. tłumaczenie niepublikowane) nie blokuje renderu headera. */
  authorName: string | null;
}

export function Header({ lang, authorName }: HeaderProps) {
  const dict = getDictionary(lang).header;

  return (
    <header className={styles.siteHeader}>
      <div className={styles.brandBlock}>
        <div className={styles.brandLogoCol}>
          <Link className={styles.brandLogoLink} href={`/${lang}`} aria-label={dict.homeAriaLabel}>
            <Image
              className={styles.brandMark}
              src="/logo.png"
              alt=""
              width={80}
              height={80}
            />
          </Link>
          <div className={styles.brandSocial}>
            <a
              className={styles.isLinkedin}
              href="#"
              aria-label={dict.linkedinAriaLabel}
              target="_blank"
              rel="noopener noreferrer"
            >
              <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                <path d="M6.94 5a1.94 1.94 0 1 1-3.88 0 1.94 1.94 0 0 1 3.88 0ZM3.5 8.5h3.4V20H3.5V8.5Zm6.2 0h3.26v1.57h.05c.45-.86 1.56-1.76 3.22-1.76 3.44 0 4.08 2.27 4.08 5.22V20h-3.4v-5.7c0-1.36-.02-3.1-1.89-3.1-1.9 0-2.19 1.48-2.19 3v5.8H9.7V8.5Z" />
              </svg>
            </a>
            <a
              className={styles.isInstagram}
              href="#"
              aria-label={dict.instagramAriaLabel}
              target="_blank"
              rel="noopener noreferrer"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} aria-hidden="true">
                <rect x="3.5" y="3.5" width="17" height="17" rx="5" />
                <circle cx="12" cy="12" r="4.2" />
                <circle cx="17.1" cy="6.9" r="0.9" fill="currentColor" stroke="none" />
              </svg>
            </a>
            <a
              className={styles.isFacebook}
              href="#"
              aria-label={dict.facebookAriaLabel}
              target="_blank"
              rel="noopener noreferrer"
            >
              <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                <path d="M14.5 21v-7.2h2.4l.36-2.8h-2.76V9.18c0-.81.22-1.36 1.39-1.36h1.48V5.32c-.26-.03-1.14-.11-2.17-.11-2.15 0-3.62 1.31-3.62 3.72v2.07H9.2v2.8h2.38V21h2.92Z" />
              </svg>
            </a>
          </div>
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
      />
    </header>
  );
}
