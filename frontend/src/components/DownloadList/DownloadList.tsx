import type { Download } from "@/lib/api/types";
import { downloadFilename } from "@/lib/format/filename";

import { DownloadButton } from "./DownloadButton";
import styles from "./DownloadList.module.css";

interface DownloadListProps {
  downloads: Download[];
  downloadLabel: string;
  downloadErrorMessage: string;
  emptyMessage: string;
}

/**
 * Lista plików do pobrania. Backend nie sanityzuje `description` jako HTML
 * (to zwykły `TextField`, `.claude/rules/security.md`) — renderowany jako
 * zwykły tekst, nigdy `dangerouslySetInnerHTML`. `file` to zawsze absolutny
 * URL (nigdy `null`, w przeciwieństwie do opcjonalnych obrazów) — link
 * pobierania renderuje się bezwarunkowo.
 */
export function DownloadList({
  downloads,
  downloadLabel,
  downloadErrorMessage,
  emptyMessage,
}: DownloadListProps) {
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
          <DownloadButton
            fileUrl={download.file}
            filename={downloadFilename(download.title, download.file)}
            label={downloadLabel}
            ariaLabel={`${downloadLabel}: ${download.title}`}
            className={styles.downloadLink}
            errorMessage={downloadErrorMessage}
            errorClassName={styles.downloadError}
            wrapperClassName={styles.downloadWrapper}
          />
        </li>
      ))}
    </ul>
  );
}
