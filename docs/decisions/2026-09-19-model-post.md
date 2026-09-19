# Model Post: PL/EN, WYSIWYG, trzy stany publikacji

- **Decyzja:** Model `Post` rozbity na część wspólną i tłumaczenia (wzorzec master + translation, biblioteka `django-parler`). Edytor treści: WYSIWYG w Django Admin. Status posta: `draft` → `published` → `archived`, **per język**.
- **Kontekst:** Blog ma być dwujęzyczny od startu (PL/EN), a treść dodaje osoba nietechniczna bez developera. Decyzja podjęta przed pierwszą migracją, bo retrofit wielojęzyczności jest kosztowny (`scope.md`).

## Struktura

**`Post`** (wspólne, niezależne od języka)
- `cover_image` — ten sam obraz dla obu wersji
- `author` — FK do `User`
- `created_at`

**`PostTranslation`** (jedna instancja na język)
- `language` — `pl` / `en`
- `title`, `slug` — slug unikalny w obrębie języka, generowany z tytułu, edytowalny
- `excerpt` — zajawka listy + fallback `meta_description` + akapit pod cytowanie przez AI (GEO)
- `content` — HTML z WYSIWYG, sanityzowany przy zapisie i serializacji
- `cover_image_alt` — opis obrazu w danym języku
- `meta_title`, `meta_description` — opcjonalne nadpisania
- `status` — `draft` / `published` / `archived`
- `published_at` — nullable
- `updated_at` — auto, per język (`dateModified` w JSON-LD liczy się per wersja)

## Uzasadnienia

- **Master + translation zamiast pól płaskich** (`title_pl`, `title_en`): 6 pól tłumaczonych × 2 języki = 12 kolumn i rosnący bałagan przy każdym nowym polu. Osobna tabela jest czystsza dla DRF i filtrowania.
- **Status per język, nie wspólny:** PL może być opublikowany od razu, a EN dorobiony tydzień później. Wspólny status blokowałby publikację PL do czasu gotowości tłumaczenia — realne tarcie przy jednym, nietechnicznym autorze.
- **`archived` zamiast kasowania:** zdjęcie posta z publikacji bez utraty treści. Publiczny queryset i tak filtruje po jednej dozwolonej wartości `status`, więc `archived` znika z API i z `sitemap.xml` bez dodatkowej logiki (`security.md`).
- **WYSIWYG, nie Markdown:** kryterium z `content-admin.md` mówi, że panel obsługuje osoba nietechniczna. Markdown wymagałby nauki składni.
- **Wspólne `id` mastera** daje za darmo: przełącznik języków na froncie (flagi PL/EN), `hreflang` wiążący wersje, i wykrycie brakującego tłumaczenia.

## Konsekwencje dla innych warstw
- API szczegółu posta musi zwracać listę dostępnych tłumaczeń (język + slug), żeby front zbudował przełącznik bez dodatkowego zapytania.
- Indeksy leżą na tłumaczeniu, nie na masterze (`performance.md`).
- `hreflang`, dynamiczny `lang` na `<html>`, sitemap tylko z opublikowanych tłumaczeń (`seo.md`).
- Frontend: `layout.tsx` ma dziś `lang="pl"` zahardkodowane — wymaga zmiany przy routingu per język.

- **Status:** aktywna.
