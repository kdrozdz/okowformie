import type { PostSummary } from "@/lib/api/types";
import type { Language } from "@/lib/i18n/languages";

import { PostCard } from "./PostCard";
import styles from "./PostList.module.css";

interface PostListProps {
  posts: PostSummary[];
  lang: Language;
  emptyMessage: string;
}

export function PostList({ posts, lang, emptyMessage }: PostListProps) {
  if (posts.length === 0) {
    return <p className={styles.empty}>{emptyMessage}</p>;
  }

  return (
    <ul className={styles.list}>
      {posts.map((post) => (
        <li key={post.slug}>
          <PostCard post={post} lang={lang} />
        </li>
      ))}
    </ul>
  );
}
