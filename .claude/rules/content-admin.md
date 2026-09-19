---
paths:
  - "backend/**/admin.py"
  - "backend/**/models.py"
  - "backend/**/forms.py"
---

# Panel redakcyjny

Posty dodaje **osoba nietechniczna**, bez pomocy developera. To jest kryterium akceptacji dla panelu, nie miły dodatek.

- Pola opisane po polsku (`verbose_name`, `help_text`) — redaktor nigdy nie widzi nazw technicznych.
- Slug generowany automatycznie z tytułu, edytowalny, ale nigdy wymagany do ręcznego wypełnienia.
- `status` z jasnym rozróżnieniem draft/published + `published_at`; publikacja to jedna świadoma akcja, nie kombinacja pól.
- Pola SEO w osobnym, zwiniętym `fieldset` z podpowiedzią limitu znaków; puste = fallback na tytuł/excerpt, nigdy pusty tag w HTML.
- Podgląd wersji roboczej dostępny dla staff przed publikacją.
- Walidacja z komunikatem po polsku mówiącym **co zrobić**, nie co się zepsuło.
- `list_display`, `list_filter` i `search_fields` ustawione tak, by dało się znaleźć post wśród setek.
- Nie wymagaj od redaktora znajomości HTML/Markdown, jeśli wybrany edytor tego nie potrzebuje — decyzja o edytorze jest w `CLAUDE.md` → Otwarte decyzje.
