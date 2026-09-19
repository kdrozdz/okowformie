# 9 — Strona „O mnie" (model + panel redakcyjny + publiczne API)

- **Cel:** Model `AboutMe` (singleton, PL/EN) + `Certificate` w nowej aplikacji `about`, panel redakcyjny w Django Admin, publiczne API `GET /api/v1/{lang}/about/`. Bez widoków frontendu — to kolejny, osobny task (frontend nie ma dziś żadnych stron bloga).
- **Status:** gotowe — implementacja, review `qa-agent`, naprawa defektów i `/code-review` zakończone. Nic nie jest scommitowane (working tree).

## Decyzje wejściowe
Pełne uzasadnienia: `docs/decisions/2026-09-19-model-about-me.md`.
- `AboutMe` (wspólne: `full_name`, `photo`) + `AboutMeTranslation` (per język: `headline`, `bio`, `photo_alt`, `meta_title`, `meta_description`, `status`, `published_at`, `updated_at`).
- Singleton: zawsze `pk=1`, admin blokuje dodanie drugiej instancji.
- `Certificate` — FK do `AboutMe`, bez tłumaczeń: `name`, `issuer`, `issued_year`, `image` (opcjonalny), `order`. `TabularInline` w adminie.
- `Language` i `PublicationStatus` (dawniej `blog.constants.PostStatus`) przenoszą się do nowego wspólnego modułu `core.constants`; `blog` importuje stamtąd.
- `status`: `draft` → `published` → `archived`, per język, ten sam cykl co `Post`.

## Plan
- [x] backend-agent: wydzielić `Language`/`PublicationStatus` z `blog.constants` do `core.constants`, zaktualizować importy w `blog/` (modele, managery, admin, testy) bez zmiany zachowania — osobny commit przed nowym kodem `about`.
- [x] backend-agent: aplikacja `about` (domenowo, wg `scope.md`) — modele `AboutMe` + `AboutMeTranslation` (`django-parler`) + `Certificate`, migracje.
- [x] backend-agent: singleton — `save()` wymusza `pk=1`, `AboutMeAdmin.has_add_permission` blokuje drugi rekord gdy już istnieje.
- [x] backend-agent: panel admina — `AboutMeAdmin` (`TranslatableAdmin`) z `CertificateInline` (`TabularInline`, sortowanie po `order`), pola po polsku, SEO w zwiniętym fieldsecie (wzorzec `blog/admin.py`). Dodatkowo: `changelist_view` przekierowuje wprost do edycji/dodania singletona (patrz „Decyzje po drodze").
- [x] backend-agent: sanityzacja `bio` (WYSIWYG) przy zapisie i serializacji — przeniesiona do `core.sanitization.sanitize_html`, `blog.sanitization.sanitize_post_html` jest teraz re-eksportem.
- [x] backend-agent: walidacja uploadu `photo`/`Certificate.image` — przeniesiona do `core.validators.validate_image_upload`, `blog.validators.validate_cover_image` jest teraz re-eksportem.
- [x] backend-agent: publiczny endpoint `GET /api/v1/{lang}/about/` (`RetrieveAPIView`, wzorzec `PostDetailView`) — 404 przy braku opublikowanego tłumaczenia, `Cache-Control`, throttling (osobny scope `about`), serializer z zagnieżdżonymi `certificates` i `available_translations`.
- [x] qa-agent: niezależne review — GO z zastrzeżeniem (patrz „Wynik review qa-agent" niżej).
- [x] backend-agent: naprawa defektów #1–#3 z review qa-agent (patrz „Naprawa defektów z review qa-agent" niżej). Defekt #4 świadomie odłożony — patrz „Do rozstrzygnięcia / poza tym branchem".
- [x] `/check` po naprawach — zielone (patrz „Wynik weryfikacji lokalnej (po naprawach)" niżej).
- [x] `/code-review` (poziom medium) — 1 znalezisko, naprawione od razu (patrz „Wynik /code-review" niżej).

## Poza zakresem tego taska
Frontend (strona `/o-mnie`), integracja z Instagramem (otwarta decyzja w `CLAUDE.md`), kategorie/tagi (nie dotyczy), generowanie treści przez AI.

## Decyzje po drodze

### Nazwa aplikacji `core` — bez kolizji
Sprawdzone (`find backend/src -iname core -o -iname about`) — nic nie istniało pod tą nazwą, zostawiona bez zmian.

### `core` dostał więcej niż tylko `Language`/`PublicationStatus`
Poza dwoma stałymi z decyzji, do `core` trafiły też:
- `core.sanitization` (`ALLOWED_TAGS`, `ALLOWED_ATTRIBUTES`, `ALLOWED_URL_SCHEMES`, `LINK_REL`, `sanitize_html`) — przeniesione z `blog.sanitization`, bo `about.bio` potrzebuje dokładnie tej samej allowlisty co `Post.content`. Dwie kopie tej samej allowlisty bezpieczeństwa byłyby dwiema prawdami o tym, co wolno w HTML z panelu.
- `core.validators` (`validate_image_upload`, `ALLOWED_IMAGE_EXTENSIONS`, `MAX_IMAGE_BYTES`) — przeniesione z `blog.validators` (`validate_cover_image`), z tego samego powodu: `about.photo` i `Certificate.image` mają identyczne wymogi co `Post.cover_image`.
- `core.api` (`LanguageURLKwargMixin`, `CacheControlMixin`) — przeniesione z `blog.views`. Nie mają nic wspólnego z postami: parsują `lang` z URL-a i dokładają `Cache-Control`. `about.views.AboutDetailView` używa ich bezpośrednio.
- `META_TITLE_MAX_LENGTH`, `META_DESCRIPTION_MIN_LENGTH`, `META_DESCRIPTION_MAX_LENGTH` — przeniesione do `core.constants`, bo `about`'s SEO fields potrzebują tych samych limitów; duplikowanie tych trzech liczb w dwóch appkach byłoby dokładnie tym ryzykiem rozjazdu, przed którym ostrzega zaktualizowana `scope.md`.

`blog/constants.py`, `blog/sanitization.py`, `blog/validators.py` zostały cienkimi modułami re-eksportującymi z `core` pod dotychczasowymi nazwami (`PostStatus`, `sanitize_post_html`, `validate_cover_image`, `MAX_COVER_IMAGE_BYTES`) — zero zmiany zachowania, zero nowej migracji w `blog` (migracja `blog/migrations/0001_initial.py` referencjonuje `blog.validators.validate_cover_image` po ścieżce importu; re-eksport pod tą samą nazwą sprawia, że import nadal się rozwiązuje). `POST_CONTENT_EXTENSIONS` (konfiguracja edytora) **nie** została przeniesiona — `about.models.BIO_CONTENT_EXTENSIONS` to świadoma kopia tego samego słownika, bo dwa użycia to jeszcze nie trzecie powtórzenie (`engineering-principles.md`); pilnuje jej niezależny `about/tests/test_editor_config.py`, tak samo jak `blog/tests/test_editor_config.py` pilnuje oryginału.

Zweryfikowane po zmianie: `ruff check`, `mypy src`, cały `pytest` bloga (96 testów) — zielone bez modyfikacji testów bloga.

### Certyfikaty: bez osobnej rejestracji w adminie
`Certificate` nie ma własnego `@admin.register` — edytowany wyłącznie przez `CertificateInline` w `AboutMeAdmin`. Drugie miejsce edycji tego samego rekordu myliłoby jedyną, nietechniczną osobę redagującą tę stronę, tak samo jak `PostTranslation` nie ma własnego wpisu w adminie obok `Post`.

### Redirect z listy `AboutMe` wprost do edycji/dodania
Zrobione (nie pominięte) — prosty `changelist_view` override: jeśli singleton istnieje, przekierowuje na `.../change/`; jeśli nie, na `.../add/`. To nie jest hack na formularzu ani na routingu, tylko standardowy redirect — lista i tak zawsze ma 0 albo 1 wiersz. `has_add_permission` blokuje bezpośrednie wejście na `add/`, gdy singleton już istnieje (Django sprawdza to samo uprawnienie w `add_view` niezależnie od tego, czy redaktor trafił tam linkiem czy wpisał adres ręcznie) — więc redirect nie otwiera furtki do obejścia blokady.

### Singleton: `save()` wymusza `pk=1`, ale `.objects.create()` nie jest tym samym co edycja
Standardowy wzorzec Django (`self.pk = SINGLETON_ID` przed `super().save()`) działa poprawnie dla zwykłego `instance.save()` (Django próbuje UPDATE, potem fallback na INSERT), co jest dokładnie tym, czego używa `ModelForm` w panelu. Nie działa z `Model.objects.create(...)` wywołanym dwa razy — `create()` jawnie przekazuje `force_insert=True`, więc druga instancja wywala się na ograniczeniu unikalności PK zamiast zaktualizować wiersz. To jest oczekiwane zachowanie Django dla „utwórz nowy”, nie defekt tego modelu; test `test_kolejny_zapis_nadpisuje_ten_sam_wiersz_zamiast_tworzyc_drugi` w `about/tests/test_models.py` używa `AboutMe(...).save()`, nie `.create()`, i to dokumentuje.

### `AboutMeManager.get_published` bez custom querysetu
W przeciwieństwie do `blog.managers.PostQuerySet` (filtruje potencjalnie setki wierszy przez `_translated_as`), `AboutMe` ma dokładnie jeden wiersz. Zamiast kopiować wzorzec query-set + `_translated_as`, `AboutMeManager.get_published()` po prostu pobiera jedyny rekord (`prefetch_related` na `translations`/`certificates`) i sprawdza tłumaczenie w pamięci — mniej kodu, ten sam efekt (404 bez fallbacku na inny język).

### `available_translations` w API bez `slug`
`blog`'s `available_translations` zawiera `{"language", "slug"}`, bo front buduje z tego link do konkretnego posta. Strona „O mnie" jest singletonem pod stałym adresem (`/o-mnie`, `/about`) niezależnie od języka — slug nie ma odpowiednika, więc `about`'s `available_translations` to `[{"language": "pl"}, ...]`.

### Rok wydania certyfikatu: walidacja dynamiczna, nie stała górna granica
`about.validators.validate_issued_year` liczy górną granicę jako `timezone.now().year` przy każdym wywołaniu (nie stałą wpisaną raz na zawsze w `MaxValueValidator`) — certyfikat „z przyszłości” nigdy nie ma być poprawny, także w kolejnych latach działania serwisu bez potrzeby aktualizacji kodu.

## Wynik weryfikacji lokalnej (2026-09-19, przed review qa-agent)

Uruchomione przez `docker compose exec -T backend uv run ...` (kontenery już działały, `docker compose ps` pokazywał `healthy`; port bazy nadal nie jest wystawiony na hosta — ograniczenie znane z `docs/tasks/7-dodanie-postu.md`, ten sam obejście).

- `ruff check .` — **All checks passed!**
- `mypy src` — **Success: no issues found in 71 source files.**
- `python manage.py check` — **System check identified no issues (2 silenced).**
- `python manage.py makemigrations --dry-run` — **No changes detected** (migracja `about/migrations/0001_initial.py` jest już wygenerowana i zaaplikowana, `blog` bez nowej migracji).
- `pytest` — **151 passed** (96 istniejących testów bloga bez zmian + 55 nowych: `about/tests/` i `core/tests/`).
- Frontend nietknięty — `npm run lint`/`typecheck`/`test` pominięte celowo (poza zakresem tego taska).

## Wynik review qa-agent (2026-09-19)

**Werdykt: GO z zastrzeżeniem.** Model, panel i publiczne API poprawne na wymiarach o największej wadze: draft/archived nie wyciekają publicznie (queryset, nie serializer), sanityzacja `bio` działa przy zapisie i odczycie, endpoint bez N+1 (≤3 zapytania), refaktor `blog`→`core` faktycznie zero-zmiany-zachowania (151 testów bloga bez modyfikacji, zielone). `pytest` — 158 passed po dodaniu testów przez qa-agenta.

**Defekt #1 (Medium) — `AboutMeAdmin.changelist_view` pomijał sprawdzenie uprawnień widoku.** `about/admin.py` — redirect do edycji/dodania liczył się **przed** `has_view_or_change_permission`, więc dowolne konto `is_staff=True` bez żadnych uprawnień do `AboutMe` dostawało `302` z adresem zawierającym PK singletona (wyciek metadanych — potwierdzenie istnienia rekordu i jego identyfikator), mimo że `change_view` i tak by zablokował faktyczny dostęp osobnym sprawdzeniem. Sprzeczne z założeniem `scope.md`, że role kont redakcyjnych będą się różnicować.

**Defekt #2 (Low) — martwa gałąź walidacji SEO w `about/forms.py` i `blog/forms.py`.** Pole modelu (`max_length`/wymagalność) odrzucało wartość na poziomie `forms.CharField` **przed** dotarciem do własnego `clean()` — przyjazny komunikat („Skróć o X znaków") nigdy się nie wyświetlał, tylko generyczny komunikat Django. Ten sam wzorzec w obu appkach (nie regresja `about` — odziedziczone z `blog`).

**Defekt #3 (Low) — weryfikacja treści obrazu (Pillow) żyła tylko w formularzu admina, nie w `core.validators`.** `Certificate(...).full_clean()` nie wykrywał podmienionej zawartości pliku pod dozwolonym rozszerzeniem — gwarancja z `security.md` trzymała się przypadkowo, tylko dzięki automatycznemu `forms.ImageField` w adminie, nie dzięki samemu walidatorowi. Nieszkodliwe dziś (jedyna droga zapisu to panel), realna luka przy drugiej ścieżce zapisu (import, przyszłe API).

**Defekt #4 (informational, nie do naprawy teraz)** — patrz „Do rozstrzygnięcia / poza tym branchem" niżej.

**Nowe testy dodane przez qa-agenta** (katalog testów, kod produkcyjny nietknięty): `about/tests/test_admin_form.py` (6 testów — poprawny formularz, podmieniona zawartość `photo`/`Certificate.image`, bardzo długi `headline`/`full_name`), `about/tests/test_admin.py::test_changelist_redirect_pomija_sprawdzenie_uprawnien_widoku` (czerwony/dokumentujący defekt #1).

## Naprawa defektów z review qa-agent (2026-09-19)

- **#1** — `AboutMeAdmin.changelist_view` (`about/admin.py`) sprawdza teraz `has_view_or_change_permission(request)` przed policzeniem przekierowania; brak uprawnień oddaje sterowanie standardowej implementacji Django (`403`), zamiast liczyć redirect z PK w adresie. Test qa-agenta zaktualizowany na `test_changelist_zwraca_403_dla_staff_bez_uprawnien_do_aboutme` (opisuje teraz poprawne zachowanie) + dodany `test_changelist_nadal_przekierowuje_do_edycji_dla_uprawnionego_konta`.
- **#2** — naprawione identycznie w `about/forms.py` i `blog/forms.py`: przyjazne komunikaty przeniesione do `Meta.error_messages` formularza (klucze `required`/`max_length`, z placeholderami `%(show_value)s`/`%(limit_value)s`). Ważny szczegół znaleziony po drodze: `error_messages` ustawiony **na polu modelu** nie działa — `Field.formfield()` w Django nie przenosi `error_messages` modelu do wygenerowanego pola formularza automatycznie, więc jedynym miejscem, gdzie te komunikaty realnie trafiają do `forms.CharField`, jest `Meta.error_messages` **formularza**. Martwe gałęzie w `_validate_seo`/`_validate_ready_to_publish` usunięte tam, gdzie faktycznie nieosiągalne; zostały tylko reguły biznesowe bez odpowiednika w polu modelu (np. `meta_description` za krótki — `min_length` nie istnieje jako ograniczenie pola).
- **#3** — `core.validators.validate_image_upload` dostał `_validate_image_content()`: otwiera obraz przez Pillow (`Image.open(...).verify()`) na **kopii** wczytanej do `BytesIO`, nie na oryginalnym uchwycie pliku — `Image.verify()` psuje obiekt do dalszego użycia, a walidator może zostać wywołany więcej niż raz na tym samym pliku w tym samym zapisie (najpierw `forms.ImageField` w adminie, potem ten sam walidator przez listę `validators=` pola modelu przy `full_clean()`). Test qa-agenta zmieniony z `test_certificate_full_clean_nie_wykrywa_podmienionej_zawartosci` na `test_certificate_full_clean_wykrywa_podmieniona_zawartosc` (po naprawie faktycznie wykrywa).

## Wynik weryfikacji lokalnej (po naprawach, 2026-09-19)

- `ruff check .` — **All checks passed!**
- `mypy src` — **Success: no issues found in 72 source files.**
- `python manage.py check` — **System check identified no issues (2 silenced).**
- `python manage.py makemigrations --dry-run` — **No changes detected.**
- `pytest -q` — **169 passed.**

## Do rozstrzygnięcia / poza tym branchem

- **Defekt #4 (informational) — teoretyczny race condition przy równoczesnym tworzeniu singletona `AboutMe`.** Dwa niemal jednoczesne submity formularza „Dodaj” mogłyby oba przejść `has_add_permission` przed zatwierdzeniem transakcji pierwszego zapisu; drugi `save()` zderzyłby się wtedy z ograniczeniem unikalności PK i skończyłby nieobsłużonym `IntegrityError` (500) zamiast komunikatem po polsku. Świadomie zaakceptowane ryzyko w fazie 1 (jeden redaktor, brak równoległych sesji admina w praktyce) — qa-agent sam rekomendował nie naprawiać teraz (test współbieżności na poziomie unit byłby niewiarygodny). Do rozważenia dopiero jeśli liczba kont redakcyjnych realnie wzrośnie (faza 2).
- Podgląd wersji roboczej dla staff (`content-admin.md`) — jak w blogu, wymaga publicznych widoków frontendu; poza zakresem, do zrobienia razem ze stroną „O mnie” na froncie.

## Wynik `/code-review` (medium, 2026-09-19)

Jedno znalezisko: `language_label()` (nazwa języka po polsku do komunikatu błędu) była zduplikowana słowo w słowo w `blog/forms.py` i `about/forms.py` — dokładnie przypadek, przed którym ostrzega dopisana dziś reguła w `scope.md` („kod potrzebny w więcej niż jednej domenie trafia do `core`"), a który przeoczyliśmy przy pierwszym przenoszeniu kodu do `core`. Naprawione od razu: nowy moduł `core/i18n.py` z jedną funkcją `language_label`, obie appki importują stamtąd; usunięty teraz-nieużywany `from django.conf import settings` w obu plikach `forms.py`. Zweryfikowane ponownie: `ruff check .` czyste, `mypy src` — 73 pliki, brak błędów, `pytest -q` — **169 passed**.

## Do zrobienia dalej
- Frontend (strona `/o-mnie`) — osobny, kolejny task.
- Commit — świadomie nie zrobiony w ramach tej sesji; do ustalenia z użytkownikiem (podział na commity: refaktor `core`, aplikacja `about`, naprawy z review, `core.i18n`, zmiany w `.claude/rules/`).
