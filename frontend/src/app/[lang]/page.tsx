import { redirect } from "next/navigation";

/**
 * `/[lang]` samo w sobie nie ma treści w mockupie (domyślnie aktywna
 * zakładka to „O mnie") — przekierowanie utrzymuje `/pl` (cel przekierowania
 * `/` z `src/proxy.ts`) sensownym miejscem docelowym zamiast martwym adresem.
 */
export default async function LangIndexPage({
  params,
}: {
  params: Promise<{ lang: string }>;
}) {
  const { lang } = await params;
  redirect(`/${lang}/o-mnie`);
}
