"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import type { Language } from "@/lib/i18n/languages";

import styles from "./Header.module.css";

interface PrimaryNavProps {
  lang: Language;
  ariaLabel: string;
  aboutLabel: string;
  postsLabel: string;
}

/**
 * Client component tylko dla aktywnego stanu linku (`usePathname()`) — reszta
 * headera zostaje server component. Prostsze niż przekazywanie bieżącej
 * ścieżki przez propsy z layoutu (który jej nie zna, patrz doc-komentarz
 * `app/[lang]/layout.tsx`).
 */
export function PrimaryNav({ lang, ariaLabel, aboutLabel, postsLabel }: PrimaryNavProps) {
  const pathname = usePathname();

  const links = [
    { href: `/${lang}/o-mnie`, label: aboutLabel },
    { href: `/${lang}/posty`, label: postsLabel },
  ] as const;

  return (
    <nav className={styles.tabs} aria-label={ariaLabel}>
      {links.map((link) => {
        const isActive = pathname === link.href || pathname.startsWith(`${link.href}/`);
        return (
          <Link
            key={link.href}
            href={link.href}
            className={isActive ? `${styles.tab} ${styles.tabActive}` : styles.tab}
            aria-current={isActive ? "page" : undefined}
          >
            {link.label}
          </Link>
        );
      })}
    </nav>
  );
}
