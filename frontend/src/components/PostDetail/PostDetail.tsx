import Image from "next/image";
import Link from "next/link";

import type { PostDetail as PostDetailData } from "@/lib/api/types";
import { formatDate } from "@/lib/format/date";
import { getDictionary } from "@/lib/i18n/dictionary";
import type { Language } from "@/lib/i18n/languages";
import { toOptimizableImageSrc } from "@/lib/media/image-src";

import styles from "./PostDetail.module.css";

interface PostDetailProps {
  post: PostDetailData;
  lang: Language;
}

/**
 * `post.content` renderowany przez `dangerouslySetInnerHTML` — bezpieczne,
 * bo API sanityzuje HTML przy serializacji, nigdy surowego pola
 * (`.claude/rules/security.md`).
 */
export function PostDetail({ post, lang }: PostDetailProps) {
  const dict = getDictionary(lang).postDetail;

  return (
    <article>
      <Link href={`/${lang}/posty`} className={styles.back}>
        &larr; {dict.back}
      </Link>

      {post.cover_image ? (
        <div className={styles.coverWrap}>
          <Image
            src={toOptimizableImageSrc(post.cover_image)}
            alt={post.cover_image_alt}
            fill
            sizes="(max-width: 720px) 100vw, 720px"
            className={styles.coverImage}
            preload
          />
        </div>
      ) : null}

      <h1 className="page-title">{post.title}</h1>
      {post.published_at ? (
        <p className={styles.date}>{formatDate(post.published_at, lang)}</p>
      ) : null}

      <div className={styles.body} dangerouslySetInnerHTML={{ __html: post.content }} />
    </article>
  );
}
