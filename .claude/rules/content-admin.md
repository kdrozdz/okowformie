---
paths:
  - "backend/**/admin.py"
  - "backend/**/models.py"
  - "backend/**/forms.py"
---

# Panel redakcyjny

Treść (posty, ale też strony takie jak „O mnie") dodaje **osoba nietechniczna**, bez pomocy developera. To jest kryterium akceptacji dla panelu, nie miły dodatek.

- Pola opisane po polsku (`verbose_name`, `help_text`) — redaktor nigdy nie widzi nazw technicznych.
- Slug generowany automatycznie z tytułu, edytowalny, ale nigdy wymagany do ręcznego wypełnienia.
- `status` z jasnym rozróżnieniem `draft` / `published` / `archived` + `published_at`; publikacja to jedna świadoma akcja, nie kombinacja pól. `archived` = zdjęcie z publikacji bez kasowania treści.
- Wersje językowe (PL/EN) edytowane w jednym miejscu, nie jako dwa osobne, niepowiązane wpisy. Redaktor musi widzieć, które wersje mają brakujące lub nieopublikowane tłumaczenie — na liście, gdy treści jest wiele, albo wprost na formularzu edycji, gdy to model-singleton bez listy. Publikacja jest per język — PL może być live, gdy EN jest jeszcze szkicem.
- Pola SEO w osobnym, zwiniętym `fieldset` z podpowiedzią limitu znaków; puste = fallback na tytuł/excerpt, nigdy pusty tag w HTML.
- Model reprezentujący dokładnie jeden byt (np. dane właściciela strony) — wzorzec singleton, nie zwykła tabela z jednym, przypadkowym rekordem: `save()` wymusza stały `pk`, a admin blokuje dodanie drugiej instancji (`has_add_permission` → `False`, gdy rekord już istnieje).
- Podgląd wersji roboczej dostępny dla staff przed publikacją.
- Walidacja z komunikatem po polsku mówiącym **co zrobić**, nie co się zepsuło.
- `list_display`, `list_filter` i `search_fields` ustawione tak, by dało się znaleźć wpis wśród wielu (nie dotyczy modeli-singletonów, gdzie nie ma listy).
- Nie wymagaj od redaktora znajomości HTML ani Markdown — edytor to WYSIWYG (`docs/decisions/2026-09-19-model-post.md`, `docs/decisions/2026-09-19-model-about-me.md`), a HTML z niego jest sanityzowany po stronie backendu (`.claude/rules/security.md`).
