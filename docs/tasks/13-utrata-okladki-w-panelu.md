# Utrata okładki przy błędzie walidacji w panelu i przycinanie obrazów

- **Cel:** panel redakcyjny ma ostrzegać redaktora, gdy wybrany obraz okładki
  zniknie z formularza po błędzie walidacji, zamiast po cichu zapisywać post
  bez okładki. Dodatkowo (zgłoszenie 2, ten sam branch): okładka posta i
  powiększenie certyfikatu mają pokazywać cały wgrany obraz, bez przycinania.
- **Status:** w toku (zgłoszenie 2 w review)

## Kontekst

Zgłoszenie: post "agata" miał dodane zdjęcie w panelu, ale nie było go widać
na froncie. Diagnoza w bazie: `cover_image` posta było puste — obraz nigdy
nie trafił do modelu, mimo że redaktorka go wybrała.

Przyczyna: `cover_image_alt` jest wymagane tylko wtedy, gdy `cover_image`
jest ustawione i post jest publikowany (`blog/forms.py`,
`_validate_ready_to_publish`). Jeśli redaktorka w jednym zapisie dołączyła
obraz, zostawiła puste `alt` i ustawiła status na "Opublikowany", formularz
odrzuca zapis błędem na `cover_image_alt`. Przeglądarka **zawsze** czyści
`<input type="file">` przy ponownym pokazaniu formularza (ograniczenie HTML,
nie Django) — więc po poprawieniu `alt` i ponownym zapisie post zapisuje się
bez żadnego błędu, ale też bez obrazu, bo plik nigdy nie wrócił do żądania.
Ten sam mechanizm dotyczy każdego innego błędu walidacji na formularzu, nie
tylko brakującego `alt`.

Po drodze sprawdzony i wykluczony drugi trop: opóźnienie w pokazaniu obrazu
na stronie posta (lista już pokazywała nowy obraz, szczegół jeszcze nie) —
to normalne opóźnienie rewalidacji ISR (do ~15s, `frontend/src/lib/api/client.ts`),
nie osobny defekt. Potwierdzone empirycznie: obraz i `alt` pojawiły się na
stronie szczegółu bez żadnej zmiany kodu, po odczekaniu na rewalidację.

## Zmiana

`backend/src/blog/forms.py` (`PostAdminForm`): nowa metoda
`_warn_if_cover_image_will_be_lost`, wołana z `clean()`. Gdy formularz
zawiera przesłany plik `cover_image` i ma jakikolwiek inny błąd walidacji
(a błąd nie dotyczy samego pola `cover_image`), dokłada czytelny komunikat
na polu `cover_image`: trzeba wybrać obraz jeszcze raz po poprawieniu
błędów, zanim zapisze się ponownie.

## Plan
- [x] Zdiagnozować, dlaczego `cover_image` posta "agata" było puste w bazie
- [x] Wykluczyć drugą hipotezę (opóźnienie ISR na stronie szczegółu)
- [x] Test odtwarzający sekwencję z posta "agata" (czerwony)
- [x] Test na ogólny przypadek (błąd na innym polu, nie tylko `cover_image_alt`)
- [x] Test kontrolny: poprawny formularz nie dostaje fałszywego ostrzeżenia
- [x] Poprawka w `PostAdminForm.clean()`
- [x] `uv run pytest` — cała suita backendu zielona
- [x] `uv run ruff check .` i `uv run mypy src` — czyste

## Decyzje po drodze
Brak zmian architektonicznych — poprawka lokalna do `blog/forms.py`, bez
zmiany kontraktu API ani schematu bazy.

---

## Zgłoszenie 2: przycinanie obrazów (okładka posta, certyfikat)

Niepowiązane ze zgłoszeniem 1 (inny mechanizm, inny obszar kodu) — dołożone
na ten sam branch/task na wyraźną decyzję, zamiast otwierać osobny task.

### Kontekst

Zgłoszenie: dodane zdjęcie w poście nie jest wyświetlane w całości; ten sam
objaw na liście postów, w szczegółach posta i w sekcji certyfikatów.
Zreprodukowane przez użytkownika: zrzut ekranu użyty jako okładka i jako
certyfikat pokazywał tylko wycentrowany fragment.

Diagnoza: w 4 niezależnych miejscach powielony ten sam wzorzec CSS —
kontener o wymuszonych proporcjach (`aspect-ratio`/stałe wymiary) +
`overflow: hidden` + `next/image (fill)` z `object-fit: cover`. `cover`
z definicji przycina obraz, gdy jego proporcje nie pasują do kontenera.
Backend niczego nie przycina (brak resize/crop w `core/image_processing.py`)
— oryginalne proporcje trafiają do frontendu.

Zasada rozstrzygająca (ustalona z `uiux-agent`): kafel-skrót w gęstej liście
→ crop dopuszczalny (pełna treść o klik dalej); widok definitywny (hero
posta, otwarty lightbox) → nigdy crop (nie ma dalszego kroku, przycięcie =
trwała utrata treści).

Przy okazji zdiagnozowany, ale **nieściągnięty do tego taska**, osobny bug:
favicon (`frontend/src/app/icon.tsx`) serwuje surowe bajty logo z API bez
faktycznego resize'u do 32×32 — przeglądarka sama dociąga center-crop.
Niepowiązane z tym zgłoszeniem (inny mechanizm — brak przetwarzania obrazu,
nie CSS), do rozważenia jako osobny task.

### Zmiana

- `frontend/src/components/PostDetail/PostDetail.module.css`:
  `.coverImage` `object-fit: cover` → `contain` (widok definitywny okładki).
  Dodane reguły `.body :global(img/figure/figcaption)` — obrazy wklejone
  przez WYSIWYG skalują się w dół zamiast przepełniać kolumnę treści.
- `frontend/src/components/CertificatesSlider/CertificatesSlider.module.css`
  i `.tsx`: `.lightboxImage` traci wymuszony `aspect-ratio: 1` (kwadrat),
  dostaje `height: min(64vh, 600px)`; `.lightboxImg` `cover` → `contain`;
  nowa klasa `.lightboxImagePlaceholder` zachowuje branded gradient w
  stanie pustym (brak zdjęcia certyfikatu).
- `.certThumbImage` (miniatura certyfikatu, kafel): zostaje `cover`, dodane
  `object-position: top`, żeby nagłówek typowego skanu dyplomu nie ginął
  w domyślnym środkowym kadrowaniu.
- `PostList.module.css` (miniatura na liście postów): świadomie bez zmian —
  kafel-skrót, crop akceptowalny.

### Plan
- [x] Zdiagnozować root cause (4 niezależne miejsca z `object-fit: cover`)
- [x] Spec UX (`uiux-agent`) — gdzie crop akceptowalny, gdzie nie
- [x] Wdrożenie (`frontend-agent`)
- [x] `npm run lint` i `npm run typecheck` — czyste
- [x] `qa-agent` review — GO, dopisane 2 testy regresyjne dla stanu pustego
      lightboksa (`CertificatesSlider.test.tsx`), pełna suita 68/68 zielona
- [x] `/code-review` (medium) — bez błędów poprawności w diffie; jedno
      znalezisko naprawione od razu (patrz niżej), reszta to follow-upy
      poza plikami tego diffa
- [x] Refaktor: 5× ręczne sklejanie klas przez template literal w
      `CertificatesSlider.tsx` → lokalny helper `cx()` (bez nowej zależności,
      identyczna kolejność klas, testy nadal zielone)
- [x] Sprawdzone na żywo (curl na działający kontener `okowformie-frontend-1`,
      hot-reload podchwycił zmiany): skompilowany CSS serwowany przez dev
      server zawiera dokładnie oczekiwane reguły — `.coverImage{object-fit:
      contain}`, `.body img{max-width:100%;...}`, `.lightboxImg{object-fit:
      contain}`, `.lightboxImagePlaceholder{...}`, `.certThumbImage{object-fit:
      cover;object-position:top}`, `.avatarPhoto{object-fit:cover}` (bez
      zmian, zgodnie z planem). Brak w tym środowisku narzędzia do sterowania
      przeglądarką (`chromium-cli` niedostępne) — to nie jest zrzut ekranu,
      tylko potwierdzenie, że właściwy CSS faktycznie dotarł do przeglądarki;
      pełny wizualny smoke-test (obraz pionowy/poziomy) zostaje do
      ręcznej weryfikacji przez użytkownika przed/po mergu.
- [ ] Merge do `dev`

### Follow-upy (świadomie nieujęte w tym tasku — inne pliki/domena)
Przeniesione do `docs/todo/TODO.md` (z `/code-review` + diagnoza favicony),
żeby nie zniknęły z kontekstu po zamknięciu tego taska — zgodnie z nową
regułą `.claude/rules/todo.md`.
