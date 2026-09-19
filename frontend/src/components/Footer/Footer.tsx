import Image from "next/image";
import Link from "next/link";

import { getDictionary } from "@/lib/i18n/dictionary";
import type { Language } from "@/lib/i18n/languages";

import styles from "./Footer.module.css";

interface FooterProps {
  lang: Language;
}

export function Footer({ lang }: FooterProps) {
  const dict = getDictionary(lang);

  return (
    <footer className={styles.siteFooter}>
      <div className={styles.footerTop}>
        <div>
          <p className={styles.footerBrandRow}>
            <Image src="/logo.png" alt="" width={28} height={28} />
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
