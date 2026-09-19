# Generowanie treści przez AI (LangChain) — osobny task

- **Decyzja:** Integracja z LangChain do automatycznego uzupełniania pól posta **nie wchodzi** w branch `7-dodanie-postu`. To osobne zadanie, realizowane po zbudowaniu modelu, panelu i CRUD-u.
- **Kontekst:** Docelowy przepływ: autor podaje tytuł (np. „Najlepsze soczewki kontaktowe w 2026 roku"), zapytanie idzie do modelu językowego, a odpowiedź — zwalidowana schematem Pydantic (structured output) — wypełnia pola posta. Człowiek przegląda, poprawia i dopiero wtedy publikuje.
- **Dlaczego osobno:** LangChain + dostawca modelu to nowa zależność w stacku, a `engineering-principles.md` każe zatrzymać się i zapytać przy takiej zmianie. Dokładanie tego do brancha, który ma dowieźć model i panel, rozdęłoby zakres jednej gałęzi.

## Ustalenia, które już obowiązują

- Model `Post` **nie wymaga żadnych zmian schematu** pod tę integrację. Pydantic i Django to dwie osobne warstwy: schemat Pydantic opisuje i waliduje odpowiedź modelu, mała funkcja mapująca przenosi ją na pola `Post`. Baza nie musi „wiedzieć" o Pydanticu.
- Pola generowane przez model: `title` (dopracowany), `excerpt`, `content`, `meta_title`, `meta_description`, `cover_image_alt`.
- Pola poza zasięgiem AI: `slug` (generowany kodem), `author`, `status`, `published_at`, `updated_at`, `cover_image` (sam plik).
- Treść wygenerowana przez AI **nigdy nie trafia od razu do `published`** — zawsze ląduje jako `draft` do weryfikacji przez człowieka.

- **Status:** aktywna. Do realizacji jako osobny branch po `7-dodanie-postu`.
