# Model AboutMe: singleton, PL/EN, certyfikaty jako osobny model

- **Decyzja:** Nowa aplikacja domenowa `about` z modelem `AboutMe` (singleton, wzorzec master + translation jak `Post` — `docs/decisions/2026-09-19-model-post.md`) i osobnym modelem `Certificate` (FK do `AboutMe`, bez tłumaczeń). `Language` i status publikacji (`draft`/`published`/`archived`) przenoszą się z `blog.constants` do wspólnego modułu `core.constants`, żeby `about` nie zależał od `blog`.
- **Kontekst:** Zakładka „O mnie" — bio autora, zdjęcie, lista certyfikatów zawodowych. Jedna, konkretna osoba (autor bloga), dwujęzyczna treść od startu (`scope.md`).

## Struktura

**`AboutMe`** (singleton, wspólne dla obu języków)
- `full_name` — imię i nazwisko, niezależne od języka
- `photo` — `ImageField`, ten sam wzorzec co `Post.cover_image` (losowa nazwa pliku pod `about/photo/`, walidacja rozszerzenia/rozmiaru)
- singleton wymuszony w `save()` (zawsze `pk=1`) i w adminie (`has_add_permission` blokuje drugą instancję)

**`AboutMeTranslation`** (jedna instancja na język)
- `headline` — np. „Optometrysta, właściciel gabinetu"
- `bio` — treść WYSIWYG, ten sam `ProseEditorField` + sanityzacja co `Post.content`
- `photo_alt` — opis zdjęcia w danym języku
- `meta_title`, `meta_description`
- `status` — `draft` / `published` / `archived`, per język
- `published_at`, `updated_at`

**`Certificate`** (osobny model, FK do `AboutMe`, bez tłumaczeń)
- `name`, `issuer` — nazwy własne, wspólne dla PL/EN (nie tłumaczy się np. „European Diploma in Optometry")
- `issued_year`
- `image` — opcjonalny skan/zdjęcie certyfikatu, ten sam wzorzec walidacji co `photo`
- `order` — ręczne sortowanie w adminie (`TabularInline`)
- Bez własnego stanu draft/published — widoczność certyfikatów wiąże się z publikacją strony `AboutMe` w danym języku; osobny cykl redakcyjny per certyfikat byłby nadmiarowy dla pojedynczej, prostej listy.

**`core.constants`** (nowy, wspólny moduł)
- `Language` i `PublicationStatus` przeniesione z `blog.constants`, `blog` importuje z `core`
- `PUBLIC_STATUS = PublicationStatus.PUBLISHED` zostaje wspólną stałą

## Uzasadnienia

- **Singleton, nie zwykła tabela:** strona dotyczy jednej, konkretnej osoby — dopuszczenie wielu rekordów tylko otwierałoby pole na przypadkowe duplikaty w adminie bez żadnego zysku dziś (YAGNI, `engineering-principles.md`).
- **Nowa app `about`, nie rozszerzenie `blog`:** `scope.md` zabrania mieszania logiki bloga z inną domeną treściową. „O mnie" nie jest postem ani jego wariantem.
- **Master + translation, nie pola płaskie:** spójne z `Post` i z zasadą przyszłościową ze `scope.md` (treść dwujęzyczna od pierwszej migracji, bez `_pl`/`_en` na płasko).
- **Certyfikaty bez tłumaczeń:** nazwa/wystawca certyfikatu to nazwa własna — tłumaczenie nie ma sensu i tylko dołożyłoby tabelę tłumaczeń bez treści do tłumaczenia.
- **Wspólny `core.constants` zamiast duplikacji:** `Language` i status publikacji to pojęcia domenowo neutralne (nie należą do bloga), potrzebne teraz w dwóch appkach. To wyjątek od „abstrakcja dopiero przy trzecim powtórzeniu" (`engineering-principles.md`): duplikacja tu nie dotyczyłaby szczegółu implementacji, tylko samego pojęcia domenowego (kody języków, cykl publikacji) — dwa niezależne źródła prawdy o tym samym konstrukcie wymagałyby ręcznej synchronizacji przy każdej zmianie, np. dojściu trzeciego języka.

## Konsekwencje dla innych warstw

- API: nowy endpoint `GET /api/v1/{lang}/about/` (pojedynczy obiekt, nie lista) — 404 gdy brak opublikowanego tłumaczenia w danym języku, tak jak przy poście bez wersji EN.
- `blog.constants.Language` i `blog.constants.PostStatus` stają się re-eksportem z `core.constants` (albo import zastępuje użycia w `blog/` — do ustalenia przy implementacji, bez zmiany zachowania ani migracji `blog`).
- Frontend: strona „O mnie" **poza zakresem tego taska** — zrobimy ją, gdy zbudujemy pozostałe widoki bloga (frontend nie ma dziś żadnych stron poza szkieletem Next.js).

- **Status:** aktywna.
