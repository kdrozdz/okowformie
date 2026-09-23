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
  downloadsLabel: string;
}

/**
 * Czysta funkcja porównania (wydzielona z JSX, żeby dało się ją przetestować
 * bez montowania komponentu/mockowania `usePathname()`). Wymaga granicy
 * `/` po `href`, nie samego prefiksu — bez tego `/pl/postyxyz` fałszywie
 * dopasowywałby się jako aktywny link do `/pl/posty` (współdzielony prefiks
 * znaków, różny segment ścieżki).
 */
export function isActiveLink(pathname: string, href: string): boolean {
  return pathname === href || pathname.startsWith(`${href}/`);
}

/**
 * Client component tylko dla aktywnego stanu linku (`usePathname()`) — reszta
 * headera zostaje server component. Prostsze niż przekazywanie bieżącej
 * ścieżki przez propsy z layoutu (który jej nie zna, patrz doc-komentarz
 * `app/[lang]/layout.tsx`).
 */
export function PrimaryNav({
  lang,
  ariaLabel,
  aboutLabel,
  postsLabel,
  downloadsLabel,
}: PrimaryNavProps) {
  const pathname = usePathname();

  const links = [
    { href: `/${lang}/o-mnie`, label: aboutLabel },
    { href: `/${lang}/posty`, label: postsLabel },
    { href: `/${lang}/do-pobrania`, label: downloadsLabel },
  ] as const;

  return (
    <nav className={styles.tabs} aria-label={ariaLabel}>
      {links.map((link) => {
        const isActive = isActiveLink(pathname, link.href);
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
