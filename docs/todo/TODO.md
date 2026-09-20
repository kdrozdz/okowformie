# To-do

Format i statusy: `README.md` w tym folderze.

## [otwarte] `about/forms.py` ma tę samą lukę utraty pliku co naprawiony bug w `blog/forms.py` (2026-09-20)
`PostAdminForm` (blog) dostał ostrzeżenie, gdy przesłany plik znika po
błędzie walidacji formularza (przeglądarka czyści `<input type="file">`
przy ponownym renderze). `about/forms.py` ma identyczną konstrukcję —
`photo` + wymagane `photo_alt` — bez żadnego ostrzeżenia. Redaktor
edytujący stronę "O mnie" może stracić zdjęcie tym samym mechanizmem, bez
ostrzeżenia. Zgodnie z `.claude/rules/scope.md` (logika potrzebna w >1
domenie → `core`, nie kopiowana per-app) — dobra okazja, żeby przy okazji
przenieść tę logikę do `core` zamiast duplikować drugi raz.

**Kontekst:** znalezisko z `/code-review` na branchu `13-utrata-okladki-w-panelu`,
opisane w `docs/tasks/13-utrata-okladki-w-panelu.md` (zgłoszenie 1 to
oryginalny fix w `blog/forms.py`).

## [otwarte] `AboutSection.module.css` nie ma reguł dla obrazów w treści WYSIWYG (`about.bio`) (2026-09-20)
`PostDetail.module.css` dostał `.body img/figure/figcaption { max-width:
100%; ... }`, żeby obrazy wklejone w treść posta przez WYSIWYG nie
przepełniały kolumny treści. `AboutSection.module.css` (`.text`, ta sama
treść WYSIWYG, `about.bio`) nie ma analogicznych reguł — ten sam defekt,
jeszcze nie zgłoszony na `/o-mnie`.

**Kontekst:** `docs/tasks/13-utrata-okladki-w-panelu.md`, sekcja
"Zgłoszenie 2" → follow-upy.

## [otwarte] Brak wspólnej konwencji `object-fit` między komponentami (2026-09-20)
`object-fit` (`cover` dla kafli, `contain` dla widoków definitywnych)
ustawiany jest niezależnie w 6+ miejscach we frontendzie. Zasada
rozstrzygająca ("kafel = cover, widok definitywny = contain") żyje tylko
w pliku planu taska, nie w kodzie — kolejne miejsce z obrazem najpewniej
skopiuje losową wartość z sąsiedztwa. Rozważyć wspólny komponent/hook
(np. `<Thumbnail>` / `<FullImage>`) po trzecim kolejnym powtórzeniu
zgodnie z `.claude/rules/engineering-principles.md` (próg już przekroczony).

**Kontekst:** `docs/tasks/13-utrata-okladki-w-panelu.md`, sekcja
"Zgłoszenie 2" → follow-upy.

## [otwarte] `PostAdminForm` tylko ostrzega o utracie pliku, nie odzyskuje go (2026-09-20)
Obecna poprawka (zgłoszenie 1) dokłada czytelny komunikat, gdy przesłany
`cover_image` zniknie po błędzie walidacji, ale nadal wymaga ponownego
wyboru pliku przez redaktora. Plik jest technicznie obecny w
`request.FILES` w momencie błędu — dałoby się go tymczasowo zachować (np.
zapis do temp storage kluczowany podpisanym tokenem) i podstawić przy
ponownym zapisie, zamiast tylko ostrzegać. Świadomie odłożone jako
głębsza zmiana wymagająca decyzji o podejściu (patrz próg "kiedy się
zatrzymać i zapytać" w `.claude/rules/engineering-principles.md`) — do
rewizji, jeśli redaktorzy będą się nadal mylić mimo ostrzeżenia.

**Kontekst:** `docs/tasks/13-utrata-okladki-w-panelu.md`, `backend/src/blog/forms.py`
(`_warn_if_cover_image_will_be_lost`), znalezisko z `/code-review`.

## [otwarte] Favicon (`icon.tsx`) serwuje surowe bajty logo bez resize'u — przeglądarka sama przycina do kwadratu (2026-09-20)
`frontend/src/app/icon.tsx` deklaruje `size = {32, 32}` jako metadaną
Next.js, ale handler zwraca surowe bajty oryginalnego pliku
`branding.logo` z API bez żadnego faktycznego resize/crop (`fetch` →
`response.arrayBuffer()` → `new Response(...)`, zero `sharp`/`canvas`/
`next/image`). Jeśli logo nie jest kwadratowe, przeglądarka sama robi
center-crop przed wyświetleniem w karcie/zakładce — stąd efekt "widać
tylko środek". Backend (`branding/models.py`) nie wymusza kwadratowych
proporcji logo, więc problem materializuje się dla dowolnego
niekwadratowego uploadu. Niepowiązane z bugiem przycinania w postach/
certyfikatach (inny mechanizm — brak przetwarzania obrazu, nie CSS).

**Kontekst:** zdiagnozowane podczas sesji naprawy przycinania obrazów
(`docs/tasks/13-utrata-okladki-w-panelu.md`), ale nieściągnięte do tego
taska. Historia decyzji o kształcie favicony: `docs/tasks/11-branding-header.md`.

## [otwarte] Rozważyć RAG dla generatora postów AI — kontekst z istniejących postów (2026-09-20)
Przy okazji taska 12 (generator postów AI) padł pomysł, żeby generowanie
korzystało z bazy wiedzy (np. dotychczasowych postów bloga) przez
retrieval-augmented generation — wyszukiwanie pasujących fragmentów w
momencie generowania i doklejanie ich do promptu. To osobny, duży temat:
wymaga bazy wektorowej, pipeline'u do embeddingów i osobnej infrastruktury,
nie jest tym samym co konfigurowalny system prompt (`AIProviderSettings`
dostał zamiast tego proste, edytowalne pole „Dodatkowe instrukcje dla AI” —
patrz `docs/tasks/12-generator-postow-ai.md`). Świadomie nieplanowane w
tasku 12 — YAGNI (`engineering-principles.md`), decyzja wejściowa #10 tego
taska już wyklucza „kontekst z istniejących postów” z zakresu.

**Kontekst:** `docs/tasks/12-generator-postow-ai.md`, rozmowa przy sekcji 6
(dodanie pola „Dodatkowe instrukcje dla AI” do `AIProviderSettings`).
