# 7 — Dodanie postu (model + panel redakcyjny)

- **Cel:** Model `Post` z tłumaczeniami PL/EN, migracje, panel redakcyjny w Django Admin z edytorem WYSIWYG. Bez publicznego API i bez widoków frontendu — to kolejne kroki.
- **Status:** w toku (branch `7-dodanie-postu`, odbity z `dev`)

## Decyzje wejściowe
Pełne uzasadnienia: `docs/decisions/2026-09-19-model-post.md`.
- `Post` (wspólne: `cover_image`, `author`, `created_at`) + `PostTranslation` (per język: `language`, `title`, `slug`, `excerpt`, `content`, `cover_image_alt`, `meta_title`, `meta_description`, `status`, `published_at`, `updated_at`).
- `status`: `draft` → `published` → `archived`, per język.
- Edytor: WYSIWYG, HTML sanityzowany przy zapisie i serializacji.
- LangChain/AI: poza tym branchem (`docs/decisions/2026-09-19-langchain-osobny-task.md`).

## Plan
- [x] backend-agent: aplikacja `blog` (domenowo, wg `scope.md`), modele `Post` + `PostTranslation`, `django-parler`, migracje.
- [x] backend-agent: rejestracja w Django Admin — pola po polsku, slug auto z tytułu, SEO w zwiniętym fieldsecie, obie wersje językowe w jednym miejscu, widoczność brakujących tłumaczeń na liście (`content-admin.md`).
- [x] backend-agent: sanityzacja HTML z WYSIWYG (allowlista, `nh3`/`bleach`) przy zapisie **i** serializacji.
- [x] backend-agent: indeksy na tłumaczeniu (`language`, `status`, `-published_at`; slug unikalny per język).
- [x] qa-agent: niezależne review zakończone (GO z zastrzeżeniem) — patrz „Wynik review qa-agent" niżej.
- [x] backend-agent: naprawić defekt #1 (auto-przypisanie autora) — czerwony test `blog/tests/test_admin.py::test_dodanie_posta_bez_wybrania_autora_ustawia_zalogowanego_uzytkownika` jest teraz zielony. Opis rozwiązania niżej w „Decyzje po drodze".
- [ ] `/check` przed uznaniem za gotowe — backend przechodzi (72 zielone, 0 czerwonych, wyniki niżej), frontend nietknięty.

## Wynik review qa-agent (2026-09-19)

**Werdykt: GO z zastrzeżeniem.** Sanityzacja HTML (zapis i odczyt, 10 wektorów XSS), filtrowanie `draft`/`archived`, walidacja uploadu (w tym podmieniona zawartość pod dozwolonym rozszerzeniem), wydajność (zmierzone 9 zapytań na changeliście z 10 postami — brak N+1), migracja `0002`, zakres faz — wszystko zweryfikowane na żywym stacku, bez zastrzeżeń.

**Defekt #1 (Medium) — auto-przypisanie autora nie działa.** `blog/admin.py:159-163` ma ustawiać `request.user` jako autora w `save_model`, ale `Post.author` nie ma `blank=True`, więc `PostAdminForm` wymusza ręczny wybór autora, zanim `save_model` się wykona — martwa gałąź. Redaktor musi przy każdym dodaniu posta ręcznie znaleźć siebie na liście. Bez utraty danych, bez dziury bezpieczeństwa — tarcie w UX panelu. Naprawa: ukryć pole `author` i zawsze podstawiać `request.user` w `save_model`, albo `initial=request.user` + `required=False` z fallbackiem w `clean()`. Przy okazji: `author` nie ma `limit_choices_to={"is_staff": True}` — w fazie 2, gdy ten sam model `User` zacznie obsługiwać klientów, dropdown pokaże też ich konta.

**Nowe testy dodane przez qa-agent** (katalog testów, `blog/` nietknięty): `test_admin.py` (czerwony test defektu), `test_querysets.py::test_slug_ktory_nigdy_nie_istnial_daje_404`, `test_admin_form.py` (bardzo długi tytuł, publikacja bez okładki, podmieniona zawartość pliku).

## Poza zakresem tego brancha
Publiczne API `/api/v1/`, widoki frontendu, przełącznik języków w UI, upload do docelowego storage (otwarta decyzja S3 vs VPS), generowanie treści przez AI.

## Do zrobienia po zakończeniu implementacji
Reguły `code-quality.md` oraz trzy zasady w `engineering-principles.md` (pojedyncza odpowiedzialność, odwrócenie zależności, diagnoza przed naprawą) powstały **po** starcie agenta budującego model — nie miał ich w kontekście. Przed review przez `qa-agent`:

- [ ] Autor implementacji przechodzi własną pracę raz jeszcze pod kątem nowych reguł: reuse (czy nie powstało coś, co już istniało), poziom abstrakcji, ścieżki błędu, pojedyncza odpowiedzialność (model nie wie o HTTP, widok nie zna szczegółów zapisu), odwrócenie zależności (media przez `STORAGES`, bez ścieżek i klienta storage na sztywno).
- [ ] Dopiero potem niezależne review przez `qa-agent` — samo-review autora go nie zastępuje.

## Decyzje po drodze

### Edytor WYSIWYG: `django-prose-editor`
Wybrany zamiast `django-ckeditor(-5)` i `django-tinymce`, bo jako jedyny z tej trójki jest na BSD bez klucza licencyjnego, serwuje assety lokalnie przez `staticfiles` (bez zewnętrznego CDN — istotne przy CSP z `security.md`) i jest aktywnie utrzymywany pod Django 6.

Konsekwencje:
- `ProseEditorField` deserializuje się do zwykłego `TextField` (`deconstruct()`), więc **zmiana edytora w przyszłości nie wymaga migracji**.
- Ustawiliśmy `sanitize=False` na polu, a sanityzację trzymamy we własnym module `blog/sanitization.py`. Powód: allowlista jest granicą bezpieczeństwa i ma być niezależna od biblioteki edytora; dwa filtry (nasz + wyprowadzony z konfiguracji edytora) to dwie prawdy o tym, co wolno. Ostrzeżenie `django_prose_editor.W004` jest świadomie wyciszone w `settings.SILENCED_SYSTEM_CHECKS` z komentarzem.
- Zestaw rozszerzeń edytora musi się **zawierać** w allowliście — inaczej redaktor formatuje tekst, zapisuje i widzi, że formatowanie zniknęło. Pilnuje tego test `blog/tests/test_editor_config.py` (tagi i atrybuty). Jedyny świadomy wyjątek: `a[rel]` — nh3 nadpisuje `rel` wartością `noopener noreferrer`, więc redaktor nie może go osłabić.

### Pole języka to parlerowe `language_code`, nie własne `language`
Decyzja mówi o polu `language`. `django-parler` buduje całe API tłumaczeń na `language_code` i bierze dla niego `choices` z `settings.LANGUAGES`. Własna nazwa oznaczałaby walkę z biblioteką bez zysku. `settings.LANGUAGES` jest jedynym źródłem prawdy; zgodność z `blog.constants.Language` pilnuje systemowy check `blog.E001` (`manage.py check`).

### `master` jako `parler.fields.TranslationsForeignKey`
Zwykły `ForeignKey` działa, ale parler ostrzega, że migracje danych nie widzą wtedy pól tłumaczonych. `TranslationsForeignKey` to podklasa FK o tym samym kształcie w bazie — migracja `0002` tylko przepina to samo ograniczenie (`DROP CONSTRAINT` + `ADD CONSTRAINT` o tej samej nazwie), bez zmiany kolumn i bez utraty danych.

### Brak fallbacku językowego (`hide_untranslated = True`, `fallbacks = []`)
Post bez opublikowanej wersji EN ma dawać 404 pod `/en/<slug>`, a nie po cichu podawać polską treść pod angielskim `hreflang` — to byłby duplikat treści w rozumieniu `seo.md`.

### Slug: własna transliteracja przed `slugify()`
Django `slugify()` normalizuje przez NFKD, a `ł`/`Ł` nie mają dekompozycji i **znikają bez śladu** („Żółty młyn" → `zoty-myn`). Stąd jawna mapa polskich znaków w `blog/slugs.py`. Unikalność liczona w obrębie języka, kolizja dostaje sufiks `-2`, `-3`; slug wpisany ręcznie nie jest po cichu zmieniany — formularz zgłasza błąd z podpowiedzią wolnego adresu.

### `on_delete=PROTECT` na `Post.author`
Skasowanie konta redaktora nie może zabrać ze sobą treści bloga.

### Naprawa defektu #1: ukryte pole `author` przy dodawaniu, nie `required=False` na formularzu
Wybrana opcja z opisu defektu: **ukryj pole `author` na formularzu dodawania i zawsze podstawiaj `request.user` w `save_model`**, zamiast `initial=` + `required=False` + fallback w `clean()`. Uzasadnienie jednym zdaniem: pole, które i tak zawsze zostanie nadpisane w `save_model`, tylko myli redaktora, sugerując wybór, który nie ma znaczenia — łatwiej i uczciwiej go nie pokazywać.

Implementacja w `blog/admin.py` (`PostAdmin`), bez zmian w `models.py` i `forms.py`:
- `get_fieldsets()` — przy dodawaniu (`obj is None`) usuwa `"author"` z listy pól pierwszego fieldsetu; przy edycji pole zostaje widoczne, żeby superuser mógł świadomie przepiąć post na innego autora (np. porządki po odejściu redaktora). Zrobione przez `get_fieldsets`, nie `get_exclude` — wykluczenie samym `exclude` zostawiłoby `"author"` w krotce `fields` fieldsetu i admin wywaliłby się `KeyError` przy renderze (pole nieobecne w formularzu, ale wciąż odwołane w fieldsetach).
- `save_model()` — fallback `if not obj.author_id: obj.author = request.user` bez warunku `not change`: przy dodawaniu formularz w ogóle nie ustawia `author` na obiekcie (pole ukryte), więc `author_id` jest puste i fallback zawsze się uruchamia; przy edycji pole jest widoczne i wymagane, więc `form.save(commit=False)` już ustawiło `author` z formularza i warunek nic nie nadpisuje.
- `formfield_for_foreignkey()` — dropdown (widoczny przy edycji) filtruje `queryset` do `is_staff=True`. To przy okazji zgłoszone w tym samym defekcie: `Post.author` nie ma `limit_choices_to`. Ograniczenie jest celowo w adminie, nie w modelu — `limit_choices_to` na `models.py` objęłoby też przyszłe programowe tworzenie postów (import, API zapisu w fazie 2), które nie powinno zakładać, że autor ma konto staff. W fazie 2, gdy ten sam `User` zacznie obsługiwać klientów, dropdown i tak pokazywałby tylko konta redakcyjne.

Czerwony test zgłoszony przez `qa-agent` nie wymagał zmian — treść bez zastrzeżeń, teraz zielony.

### `django-stubs` dołożone do dev-dependencies
Bez wtyczki `mypy_django_plugin` mypy czytał `TextChoices` jako krotki i sypał 20 fałszywymi błędami — „mypy clean" nic by wtedy nie znaczyło. Ponieważ `django-parler` nie ma `py.typed`, jego klasy bazowe są dla mypy `Any`; w dwóch miejscach trzeba było to obejść jawnie i z komentarzem (`_PostManagerBase` w `blog/managers.py`, `_default_manager` w `blog/models.py`). Dodatkowo `accounts.User` dostał deklarację relacji odwrotnej `posts` (tylko pod `TYPE_CHECKING`).

### `ruff format` nie dotyka katalogu migracji
`.claude/settings.json` zabrania edycji migracji, a `ruff format` chciał je przeformatować przy każdym `makemigrations`. Wykluczone w `pyproject.toml` (plus `I001` w `per-file-ignores`) — spójne z komentarzem, który już tam był.

## Rozstrzygnięte przez użytkownika (2026-09-19)

- **Język kodu vs komentarzy** — kod (klasy, funkcje, zmienne, pola) i commity po angielsku; komentarze mogą być po polsku. `conventions.md` zaktualizowana. Weryfikacja: nazewnictwo w `blog/` już było po angielsku (`PostQuerySet`, `sanitize_post_html`, `build_unique_slug` itd.) — jedyne odstępstwo to celowe `status_pl`/`status_en` w `admin.py`, bo nazwa opisuje treść widoczną dla redaktora w panelu (dozwolony wyjątek w regule). Zero kodu do zmiany.
- **`django-stubs` jako zależność dev** — zaakceptowane. Zostaje w projekcie, standardowe narzędzie do typowania Django (`TextChoices`, `choices`), dev-only.

## Do rozstrzygnięcia / poza tym branchem

- **Podgląd wersji roboczej dla staff** (`content-admin.md`) — nie da się zrobić bez publicznych widoków. Do zrobienia razem ze stroną posta.
- **Redirect 301 po zmianie slugu** (`seo.md`) — wymaga historii slugów; do zaplanowania razem z routingiem frontu. Na razie `help_text` ostrzega redaktora, żeby nie zmieniał slugu po publikacji.
- **`MEDIA_ROOT` w produkcji** — domyślnie `backend/media/`, co jest wygodne w dev, ale `security.md` wymaga katalogu poza aplikacją, serwowanego przez reverse proxy/CDN. Zmienna jest w `backend/env.example`; ustawienie jej to zadanie dla `infra-agent` przy deployu.
- **Port bazy nie jest wystawiony na hosta** — `pytest` na macOS nie ma jak się połączyć (39 testów kończy się błędem połączenia). Testy uruchamiamy przez `docker compose exec -T backend uv run pytest`. Jeśli ma działać z hosta, `infra-agent` musi odkomentować `ports:` przy usłudze `db`.
