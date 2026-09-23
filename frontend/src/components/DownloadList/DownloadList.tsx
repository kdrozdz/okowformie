import type { Download } from "@/lib/api/types";

import styles from "./DownloadList.module.css";

interface DownloadListProps {
  downloads: Download[];
  downloadLabel: string;
  emptyMessage: string;
}

/**
 * Lista plików do pobrania. Backend nie sanityzuje `description` jako HTML
 * (to zwykły `TextField`, `.claude/rules/security.md`) — renderowany jako
 * zwykły tekst, nigdy `dangerouslySetInnerHTML`. `file` to zawsze absolutny
 * URL (nigdy `null`, w przeciwieństwie do opcjonalnych obrazów) — link
 * pobierania renderuje się bezwarunkowo.
 */
export function DownloadList({ downloads, downloadLabel, emptyMessage }: DownloadListProps) {
  if (downloads.length === 0) {
    return <p className={styles.empty}>{emptyMessage}</p>;
  }

  return (
    <ul className={styles.list}>
      {downloads.map((download) => (
        <li key={download.file} className={styles.card}>
          <div className={styles.body}>
            {/* Tytuł jako H2 — lista ma jeden H1 na stronę, karty go nie duplikują. */}
            <h2 className={styles.title}>{download.title}</h2>
            {download.description ? (
              <p className={styles.description}>{download.description}</p>
            ) : null}
          </div>
          <a href={download.file} download className={styles.downloadLink}>
            {downloadLabel}
          </a>
        </li>
      ))}
    </ul>
  );
}
