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

## GEO (AI search / chat)
- `robots.txt` dopuszcza boty AI (`GPTBot`, `ClaudeBot`, `PerplexityBot`, `Google-Extended`), chyba że świadomie zablokowane.
- `Article` JSON-LD z aktualnym `datePublished`/`dateModified` — modele AI ważą świeżość mocniej niż klasyczny ranking.
- Treść posta zaczyna się od wprost sformułowanej odpowiedzi/definicji, nie od wstępu — ułatwia cytowanie przez AI.
