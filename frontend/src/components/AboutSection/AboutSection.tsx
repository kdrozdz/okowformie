import Image from "next/image";

import { CertificatesSlider } from "@/components/CertificatesSlider/CertificatesSlider";
import type { About } from "@/lib/api/types";
import { getDictionary } from "@/lib/i18n/dictionary";
import type { Language } from "@/lib/i18n/languages";

import styles from "./AboutSection.module.css";

interface AboutSectionProps {
  about: About;
  lang: Language;
}

/**
 * `about.bio` renderowany przez `dangerouslySetInnerHTML` — bezpieczne,
 * bo API sanityzuje HTML przy serializacji (allowlist tagów, `nh3`/`bleach`
 * po stronie backendu, `.claude/rules/security.md`), nigdy surowego pola.
 */
export function AboutSection({ about, lang }: AboutSectionProps) {
  const dict = getDictionary(lang).certificates;

  return (
    <>
      <h1 className="page-title">{about.full_name}</h1>
      {about.headline ? <p className={styles.headline}>{about.headline}</p> : null}

      <div className={styles.about}>
        <div className={styles.avatarWrap}>
          <div className={styles.blob} aria-hidden="true" />
          <div className={styles.avatar}>
            {about.photo ? (
              <Image
                className={styles.avatarPhoto}
                src={about.photo}
                alt={about.photo_alt}
                width={108}
                height={108}
                preload
              />
            ) : (
              <svg
                className={styles.avatarPlaceholder}
                viewBox="0 0 24 24"
                fill="none"
                aria-hidden="true"
              >
                <path
                  d="M2 12C4.5 7 8 4.5 12 4.5S19.5 7 22 12C19.5 17 16 19.5 12 19.5S4.5 17 2 12Z"
                  stroke="white"
                  strokeWidth={1.4}
                />
                <circle cx="12" cy="12" r="3.4" fill="white" />
              </svg>
            )}
          </div>
        </div>
        <div className={styles.text} dangerouslySetInnerHTML={{ __html: about.bio }} />
      </div>

      {about.certificates.length > 0 ? (
        <div className={styles.courses}>
          <div className={styles.coursesHeader}>
            <div className={styles.coursesHeading}>
              <h2 className={styles.coursesTitle}>{dict.heading}</h2>
              <div className={styles.coursesCount}>
                <span className={styles.coursesCountNumber}>{about.certificates.length}</span>
                <span className={styles.coursesCountLabel}>{dict.countLabel}</span>
              </div>
            </div>
          </div>
          <CertificatesSlider certificates={about.certificates} dict={dict} />
        </div>
      ) : null}
    </>
  );
}
