---
description: Audyt SEO i GEO strony bloga przez seo-agent — metadane, dane strukturalne, sitemap, CWV, widoczność w AI search.
argument-hint: [opcjonalnie: ścieżka lub komponent do zawężenia]
allowed-tools: Read, Grep, Glob, Bash, Agent
---

Zakres audytu: $ARGUMENTS (pusty = cały frontend)

Deleguj do `seo-agent`. Wymagaj sprawdzenia:

1. Metadane na stronie posta i liście — title, description, canonical, OG/Twitter.
2. `Article` JSON-LD — obecność i poprawność pól wymaganych przez Google.
3. `sitemap.xml` i `robots.txt` — czy generowane, czy zawierają tylko opublikowane posty (drafty nie mogą wyciekać).
4. Hierarchia nagłówków, alt text obrazów.
5. Obsługa zmiany sluga — czy istnieje redirect 301.
6. Core Web Vitals — miejsca ryzyka (brak `priority` na LCP, brak wymiarów obrazu → CLS).
7. GEO — `robots.txt` dopuszcza boty AI (`GPTBot`, `ClaudeBot`, `PerplexityBot`), `llms.txt`, świeżość `dateModified`, czy treść zaczyna się od wprost sformułowanej odpowiedzi (pod cytowanie przez AI).

## Wyjście

Lista konkretnych poprawek z lokalizacją `plik:linia` i priorytetem. `seo-agent` nie edytuje kodu — wdrożenie zleć `frontend-agent` po akceptacji listy.
