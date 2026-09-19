---
paths:
  - "frontend/**"
---

# SEO

- Slugi: unikalne, generowane z tytułu, edytowalne. Zmiana sluga → redirect 301 ze starego adresu.
- Metadane: OG/Twitter, canonical URL, `sitemap.xml`, `robots.txt`, RSS, `Article` JSON-LD.
- Meta title ≤ 60 znaków, meta description 150–160 znaków.
- Hierarchia nagłówków H1–H6 bez przeskoków; jeden H1 na stronę.
- Obrazy: `alt` opisowy, nie pusty i nie nazwa pliku.

## Wielojęzyczność (PL/EN)
- `hreflang` na każdej stronie posta: wzajemne odnośniki PL↔EN + `x-default`. Bez tego Google traktuje wersje jako konkurujące duplikaty.
- Tylko **opublikowane** tłumaczenia trafiają do `hreflang` i do `sitemap.xml` — brak wersji EN albo EN w statusie `draft`/`archived` oznacza brak wpisu, nie link do pustej strony.
- Atrybut `lang` na `<html>` ustawiany dynamicznie per język strony, nie zahardkodowany.
- Slug osobny per język (unikalny w obrębie języka), nie tłumaczony automatycznie z PL.

## GEO (AI search / chat)
- `robots.txt` dopuszcza boty AI (`GPTBot`, `ClaudeBot`, `PerplexityBot`, `Google-Extended`), chyba że świadomie zablokowane.
- `Article` JSON-LD z aktualnym `datePublished`/`dateModified` — modele AI ważą świeżość mocniej niż klasyczny ranking.
- Treść posta zaczyna się od wprost sformułowanej odpowiedzi/definicji, nie od wstępu — ułatwia cytowanie przez AI.
