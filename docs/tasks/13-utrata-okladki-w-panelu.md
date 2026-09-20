# Utrata okładki przy błędzie walidacji w panelu

- **Cel:** panel redakcyjny ma ostrzegać redaktora, gdy wybrany obraz okładki
  zniknie z formularza po błędzie walidacji, zamiast po cichu zapisywać post
  bez okładki.
- **Status:** gotowe

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
