import Image from "next/image";
import Link from "next/link";

import { formatDate } from "@/lib/format/date";
import type { PostSummary } from "@/lib/api/types";
import type { Language } from "@/lib/i18n/languages";

import styles from "./PostList.module.css";

interface PostCardProps {
  post: PostSummary;
  lang: Language;
}

/** Tytuł karty jako H2 — lista ma jeden H1 na stronę, karty go nie duplikują. */
export function PostCard({ post, lang }: PostCardProps) {
  return (
    <Link href={`/${lang}/posty/${post.slug}`} className={styles.card}>
      <span className={styles.thumbWrap}>
        {post.cover_image ? (
          <Image
            src={post.cover_image}
            alt={post.cover_image_alt}
            fill
            sizes="112px"
            className={styles.thumbImage}
          />
        ) : null}
      </span>
      <span className={styles.body}>
        <h2 className={styles.title}>{post.title}</h2>
        <p className={styles.excerpt}>{post.excerpt}</p>
        {post.published_at ? (
          <p className={styles.date}>{formatDate(post.published_at, lang)}</p>
        ) : null}
      </span>
    </Link>
  );
}
