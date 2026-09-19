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
- `status` z jasnym rozróżnieniem `draft` / `published` / `archived` + `published_at`; publikacja to jedna świadoma akcja, nie kombinacja pól. `archived` = zdjęcie z publikacji bez kasowania treści.
- Wersje językowe (PL/EN) edytowane w jednym miejscu, nie jako dwa osobne, niepowiązane wpisy. Redaktor musi widzieć na liście, które posty mają brakujące lub nieopublikowane tłumaczenie. Publikacja jest per język — PL może być live, gdy EN jest jeszcze szkicem.
- Pola SEO w osobnym, zwiniętym `fieldset` z podpowiedzią limitu znaków; puste = fallback na tytuł/excerpt, nigdy pusty tag w HTML.
- Podgląd wersji roboczej dostępny dla staff przed publikacją.
- Walidacja z komunikatem po polsku mówiącym **co zrobić**, nie co się zepsuło.
- `list_display`, `list_filter` i `search_fields` ustawione tak, by dało się znaleźć post wśród setek.
- Nie wymagaj od redaktora znajomości HTML ani Markdown — edytor to WYSIWYG (`docs/decisions/2026-09-19-model-post.md`), a HTML z niego jest sanityzowany po stronie backendu (`.claude/rules/security.md`).
