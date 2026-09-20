import Image from "next/image";
import Link from "next/link";

import type { Branding } from "@/lib/api/types";
import { getDictionary } from "@/lib/i18n/dictionary";
import type { Language } from "@/lib/i18n/languages";
import { toOptimizableImageSrc } from "@/lib/media/image-src";

import styles from "./Footer.module.css";

interface FooterProps {
  lang: Language;
  /** Ten sam obiekt co `HeaderProps.branding` (patrz `Header.tsx`) — jedno
   * pobranie w `layout.tsx`, dzielone przez header i footer. `null` = błąd
   * pobrania, fallback na statyczne `public/brand/logo.png`. */
  branding: Branding | null;
}

export function Footer({ lang, branding }: FooterProps) {
  const dict = getDictionary(lang);
  const logoSrc = branding?.logo ? toOptimizableImageSrc(branding.logo) : "/brand/logo.png";

  return (
    <footer className={styles.siteFooter}>
      <div className={styles.footerTop}>
        <div>
          <p className={styles.footerBrandRow}>
            <Image src={logoSrc} alt="" width={28} height={28} />
            <span>okowFormie</span>
          </p>
          <p className={styles.footerTagline}>{dict.footer.tagline}</p>
        </div>

        <nav className={styles.footerLinks} aria-label={dict.header.navAriaLabel}>
          <Link href={`/${lang}/o-mnie`}>{dict.header.navAbout}</Link>
          <Link href={`/${lang}/posty`}>{dict.header.navPosts}</Link>
        </nav>
      </div>

      <div className={styles.footerBottom}>
        <p>{dict.footer.copyright}</p>
      </div>
    </footer>
  );
}
