import Link from "next/link";

import type { Language } from "@/lib/i18n/languages";

import styles from "./Pagination.module.css";

interface PaginationProps {
  lang: Language;
  currentPage: number;
  hasPrevious: boolean;
  hasNext: boolean;
  previousLabel: string;
  nextLabel: string;
  ariaLabel: string;
}

export function Pagination({
  lang,
  currentPage,
  hasPrevious,
  hasNext,
  previousLabel,
  nextLabel,
  ariaLabel,
}: PaginationProps) {
  if (!hasPrevious && !hasNext) {
    return null;
  }

  return (
    <nav className={styles.pagination} aria-label={ariaLabel}>
      {hasPrevious ? (
        <Link href={`/${lang}/posty?page=${currentPage - 1}`} className={styles.link}>
          &larr; {previousLabel}
        </Link>
      ) : (
        <span className={styles.spacer} aria-hidden="true" />
      )}
      {hasNext ? (
        <Link href={`/${lang}/posty?page=${currentPage + 1}`} className={styles.link}>
          {nextLabel} &rarr;
        </Link>
      ) : (
        <span className={styles.spacer} aria-hidden="true" />
      )}
    </nav>
  );
}
