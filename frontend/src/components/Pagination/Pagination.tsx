import Link from "next/link";

import styles from "./Pagination.module.css";

interface PaginationProps {
  /** Ścieżka listy bez query string, np. `/pl/posty` albo `/pl/do-pobrania` — komponent dokleja tylko `?page=`. */
  basePath: string;
  currentPage: number;
  hasPrevious: boolean;
  hasNext: boolean;
  previousLabel: string;
  nextLabel: string;
  ariaLabel: string;
}

export function Pagination({
  basePath,
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
        <Link href={`${basePath}?page=${currentPage - 1}`} className={styles.link}>
          &larr; {previousLabel}
        </Link>
      ) : (
        <span className={styles.spacer} aria-hidden="true" />
      )}
      {hasNext ? (
        <Link href={`${basePath}?page=${currentPage + 1}`} className={styles.link}>
          {nextLabel} &rarr;
        </Link>
      ) : (
        <span className={styles.spacer} aria-hidden="true" />
      )}
    </nav>
  );
}
