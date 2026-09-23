# 15 — Motyw i czytelność panelu Django Admin (okowFormie)

- **Cel:** panel redakcyjny (Django Admin) ma dostać wizualny motyw zgodny z
  marką okowFormie (kolory, logo, nagłówki), czytelniejszą stronę główną
  (modele pogrupowane w kategorie, nie płaska lista wg nazwy apki Django),
  **oraz** lepszą czytelność samych formularzy: pola przyjmujące więcej
  tekstu dostają większe widgety, opisy pól (`help_text`) są uzupełnione tam,
  gdzie ich brakuje, a listy dostają filtry/wyszukiwanie, gdzie dziś ich nie
  ma i realnie ułatwiłyby odnalezienie wpisu. Wyłącznie warstwa
  wizualna/nawigacyjna i UX formularzy — bez zmian w logice biznesowej,
  walidacji czy schemacie bazy.
- **Status:** w toku — plan czeka na akceptację przed implementacją.

## Kontekst

Panel działa dziś na stockowym wyglądzie Django Admin (brak `site_header`,
`site_title`, logo, kolorów marki) pod niestandardowym URL-em
(`ADMIN_URL` = `panel-redakcyjny/`, `.claude/rules/security.md`).

Funkcjonalna warstwa UX per model jest już mocno dopracowana zgodnie z
`.claude/rules/content-admin.md`: polskie etykiety, kolorowe kropki statusu
w `blog/admin.py` (`_STATUS_COLORS`), podgląd ikonki platformy w
`branding/admin.py` (`SocialLinkInline.platform_icon`), singletony z
redirectem z listy 1-elementowej do edycji (`about`, `branding`,
`ai_content`). Ten task **nie** dotyka tej warstwy — dotyczy wyglądu i
nawigacji całego panelu jako jednej powierzchni, żeby osoba nietechniczna
(`content-admin.md`) rozpoznawała „swój" panel, a nie generyczny Django
Admin, i żeby odnalezienie właściwej sekcji (blog vs. „O mnie" vs. branding
vs. AI vs. konta) nie wymagało znajomości nazw apek Django.

## Decyzje wejściowe

- **Bez nowej zależności w stacku** — własny override szablonów/CSS Django
  Admin, nie gotowy pakiet (django-unfold/jazzmin). Decyzja użytkownika po
  pytaniu wprost (`.claude/rules/engineering-principles.md`: nowa zależność
  wymaga zgody przed implementacją).
- **Kolory** — skopiowane z tokenów frontendu (`frontend/src/app/globals.css`):
  teal `#2e8b90`, indigo `#5b4fa0`, navy `#1f2b57`, ink `#232838`, tło
  `#f4f3fa`, powierzchnia `#ffffff`. Nowa kopia w CSS admina, nie wspólny
  plik — Django Admin i Next.js to inny build/runtime, nie da się ich podłączyć
  pod jedno źródło bez dodatkowej infrastruktury. Ryzyko rozjazdu przy
  przyszłej zmianie brandu odnotowane w „Poza zakresem" niżej.
- **Czcionki** — system font stack, bez ładowania Google Fonts (Sora/Karla)
  w adminie: uniknięcie nowego hosta w CSP (`.claude/rules/security.md`:
  brak `unsafe-inline`/zbędnych hostów). Motyw dopasowany kolorystycznie,
  nie typograficznie 1:1 z frontendem.
- **Logo w headerze** — statyczny plik (`backend/src/backend/static/admin/...`),
  **nie** dynamiczne `branding.models.SiteBranding.logo` z bazy: unika
  dodatkowego zapytania do bazy na każde renderowanie każdej strony panelu
  (`.claude/rules/performance.md`) dla korzyści bez praktycznego znaczenia
  (panel nie jest publiczny, ogląda go jedna osoba redakcyjna). Zmiana logo
  marki w przyszłości = ręczna aktualizacja tego jednego statycznego pliku —
  świadomy koszt, nie luka.
- **Grupowanie stron głównej** — własne kategorie („Treść", „Branding",
  „Konfiguracja AI", „Konta") przez nadpisanie `AdminSite.get_app_list`,
  zamiast domyślnego grupowania Django po nazwie apki. To jest główny cel
  taska pod kątem czytelności.
- **Rozmiar widgetów wg długości treści** — reguła do zastosowania
  konsekwentnie we wszystkich apkach: pole na kilka zdań/dłuższy tekst
  dostaje `Textarea` (wzorzec już istnieje: `excerpt` w `blog/forms.py`,
  `extra_instructions` w `ai_content/models.py`), pole na jedną frazę
  zostaje `TextInput` powiększonym `size` (wzorzec: `cover_image_alt`/
  `photo_alt`, `attrs={"size": 80}`). Krótkie pola (np. `Rok wydania`,
  `Kolejność`) zostają bez zmian — powiększanie ich nie pomaga w
  odnalezieniu się, tylko zajmuje miejsce.

Znaleziska z audytu obecnego kodu (do naprawy w kroku backend-agenta niżej):
- `meta_title`/`meta_description` w `blog/forms.py` i `about/forms.py` **nie
  mają** nadpisanego widgetu — renderują się jako domyślny, wąski
  `TextInput`, mimo że to pola na pełne zdanie (do 60/160 znaków). Reszta
  pól tej długości w tych samych formularzach już ma powiększony widget —
  to niespójność, nie świadomy wybór.
- `ai_content/models.py::AIProviderSettings.extra_instructions` ma
  `Textarea(rows=4)`, ale domyślna treść pola to już 2 zdania — realna
  instrukcja redaktora będzie dłuższa; `rows` do zwiększenia.
- `about/models.py::Certificate.issuer` nie ma `help_text` (jedyne pole
  certyfikatu bez opisu, obok `name`/`image`/`order`, które go mają).
- `ai_content/forms.py::PostGenerationForm` (`topic`, `local_focus`) nie ma
  `help_text` — tylko `label` i komunikaty błędów; redaktor nie ma
  podsumowania, co te pola robią, dopóki nie kliknie i nie dostanie błędu.

## Plan

- [ ] **uiux-agent** — spec: mapowanie tokenów kolorów frontendu na role
      Django Admin (header, przyciski, linki, focus states, istniejące
      kolorowe kropki statusu w `blog`/`branding` — zostają czy dostają
      nową paletę?), układ i kolejność kategorii na stronie głównej, miejsce
      i rozmiar logo (header + strona logowania), kontrast WCAG AA na
      nowych kolorach (szczególnie tekst/przyciski na `--navy`/`--indigo`),
      decyzja czy dark mode (Django Admin ma go domyślnie) dostaje własne
      kolory czy zostaje na domyślnych Django. Dodatkowo: reguła rozmiaru
      widgetu wg długości treści (Textarea vs. TextInput powiększony,
      liczba `rows`) i przegląd każdej listy (`PostAdmin`, stockowy
      `UserAdmin`) pod kątem brakujących, realnie użytecznych filtrów/
      `search_fields` — lista konkretnych rekomendacji do wdrożenia w
      kroku backend-agenta.
- [x] **backend-agent** — implementacja wg spec:
  - `admin.site.site_header` / `site_title` / `index_title` — branding
    okowFormie, jedno miejsce (`backend/src/backend/admin.py` lub `apps.py`
    → `ready()`).
  - Nadpisanie `get_app_list` (custom `AdminSite` albo monkeypatch
    `admin.site.get_app_list`) — grupowanie wg spec z kroku 1.
  - `templates/admin/base_site.html` (wzorzec nadpisania szablonu już
    istnieje w `ai_content/templates/admin/ai_content/postgenerator/changelist.html`)
    — logo w headerze.
  - `static/admin/css/okowformie-admin.css`, dołączony przez `Media`/
    `extrahead` — kolory ze spec. Bez dotykania JS/zachowania istniejących
    collapsed fieldsets, inline formsetów (`SocialLinkInline`,
    `CertificateInline`) — czysto wizualne nadpisanie.
  - Ujednolicenie wizualne między apkami **tylko jeśli** spec z kroku 1 to
    obejmie (np. `about`/`ai_content` bez kolorowych statusów, które ma
    `blog`/`branding`) — bez dobudowywania nowych funkcji poza czytelność.
  - Powiększenie widgetów `meta_title`/`meta_description` (`blog/forms.py`,
    `about/forms.py`) do tego samego wzorca co `excerpt`/`cover_image_alt`
    (Textarea albo `TextInput(size=80)`, zależnie od spec), zwiększenie
    `rows` na `extra_instructions` (`ai_content/models.py`).
  - Dopisanie brakujących `help_text`: `Certificate.issuer`
    (`about/models.py`), `topic`/`local_focus` (`ai_content/forms.py`).
  - Dodanie filtrów/`search_fields` z rekomendacji `uiux-agent` tam, gdzie
    audyt wykaże realny brak (np. wyszukiwanie postów po autorze/nazwie
    użytkownika w `PostAdmin.search_fields`, jeśli spec to potwierdzi) —
    bez dodawania filtrów „na wszelki wypadek" tam, gdzie lista i tak ma
    kilka wierszy (singletony `about`/`branding`/`ai_content` bez zmian).
- [x] **qa-agent** — testy: render strony głównej panelu (kategorie w
      oczekiwanej kolejności/nazwach, każda apka widoczna w swojej grupie),
      render `base_site.html` (logo, `site_header` w treści odpowiedzi),
      regresja istniejących `test_admin.py` (about/blog/branding/ai_content)
      — zielone bez zmian, kontrola uprawnień niezmieniona (grupowanie nie
      ujawnia apek/modeli bez uprawnień — `has_module_permission` per apka
      musi nadal działać tak jak dziś, w tym `PostGeneratorAdmin`). Nowe
      filtry/`search_fields` (jeśli dodane) dostają test na faktyczne
      zawężenie wyniku, nie tylko na obecność w konfiguracji.
- [ ] `/check` (backend: ruff, mypy, `manage.py check`, pytest,
      `makemigrations --check` — bez zmian schematu, więc czysto).
- [ ] `/code-review` (qa-agent nie recenzuje własnego kodu —
      `code-quality.md`).
- [ ] Sprawdzone na żywo w przeglądarce (`docker compose up`, panel pod
      `ADMIN_URL`) — strona logowania, strona główna, przynajmniej jeden
      formularz edycji (np. `Post`) z nowym motywem, zanim task zamknięty
      jako gotowy.

## Kryteria akceptacji

- Panel ma spójny motyw kolorystyczny marki okowFormie (nie stockowy Django
  Admin), logo widoczne w headerze i na stronie logowania.
- Strona główna panelu grupuje modele w czytelne kategorie zamiast płaskiej
  listy wg nazwy apki Django.
- Zero zmian funkcjonalnych: uprawnienia, walidacja, workflow singletonów
  (`about`, `branding`, `ai_content.AIProviderSettings`), generator AI
  (`PostGeneratorAdmin`) — działają identycznie jak dziś.
- Zero regresji: pełna suita `pytest` zielona, `ruff`/`mypy` czyste, **żadna
  nowa zależność** w `pyproject.toml`/`uv.lock`.
- Kontrast kolorów WCAG AA (tekst na tle, przyciski, linki) — potwierdzone w
  specu `uiux-agent`, zweryfikowane na żywo.
- Panel wciąż dostępny wyłącznie pod niestandardowym URL-em (`ADMIN_URL`) —
  brak zmian w konfiguracji z `security.md`.
- Pola przyjmujące dłuższy tekst (`meta_title`, `meta_description`,
  `extra_instructions`) mają widget dopasowany do długości treści, zgodnie
  ze wzorcem już istniejącym dla `excerpt`/`cover_image_alt`/`photo_alt`.
  Krótkie pola (liczby, kolejność) zostają bez zmian.
- Każde pole formularza w `blog`/`about`/`ai_content` ma `help_text` po
  polsku — zero pól bez opisu (`Certificate.issuer`, `PostGenerationForm`
  naprawione, reszta potwierdzona jako już kompletna).
- Listy w panelu mają filtry/wyszukiwanie odpowiadające temu, jak redaktor
  faktycznie szuka treści — bez dodawania filtrów do list, które i tak mają
  0–1 wiersz (singletony).

## Poza zakresem

- Dashboard z widgetami/statystykami (liczba szkiców, ostatnie posty) —
  naturalny follow-up, ale nowa funkcja, nie „czytelność" — osobne
  zlecenie, jeśli zapadnie taka decyzja.
- Synchronizacja tokenów kolorów między frontendem i adminem (dwa źródła
  prawdy, bez wspólnego pliku) — świadomie odłożone; jeśli po zamknięciu
  taska nadal aktualne, dopisać do `docs/todo/TODO.md`.
- Dynamiczne logo z `branding.SiteBranding` w headerze admina — patrz
  decyzja wejściowa wyżej (koszt zapytania do bazy na każde renderowanie
  strony, brak realnej korzyści dla panelu niepublicznego).

## Decyzje po drodze

### Spec kolorów/layoutu (krok 1 planu)

`uiux-agent` zawiesił się dwa razy pod rząd (stream watchdog, brak
odpowiedzi) — bez trzeciej próby na tym samym zadaniu. Spec przygotowany
bezpośrednio, na tych samych danych (tokeny z `frontend/src/app/globals.css`,
istniejące hexy w `blog/admin.py`/`branding/admin.py`, kontrast liczony
wg formuły WCAG — luminancja względna + `(L1+0.05)/(L2+0.05)`).

**Kolory (zmienne CSS Django Admin, `admin/css/base.css`):**
| Zmienna | Wartość | Uzasadnienie |
|---|---|---|
| `--header-bg` | `#1f2b57` (navy) | Biały tekst na navy → kontrast 13.7:1 (AAA) |
| `--header-color`, `--header-link-color`, `--header-branding-color` | `#ffffff` | — |
| `--link-fg` | `#5b4fa0` (indigo) | Indigo na białym tle → 6.84:1 (AA, blisko AAA) |
| `--link-hover-color` | `#1f2b57` (navy) | Ciemniejszy hover, zawsze AA |
| `--primary` / `--button-bg` | `#5b4fa0` (indigo) | Biały tekst na indigo → 6.84:1 (AA) |
| `--button-hover-bg` | `#46397d` (indigo −15%) | — |
| `--default-button-bg` (drugi przycisk submit) | `#1f2b57` (navy) | Biały tekst → 13.7:1 |
| `--default-button-hover-bg` | `#16204a` | — |
| `--delete-button-bg` | **bez zmian** (`#ba2121`, domyślny czerwony Django) | Kolor "usuń" to semantyka bezpieczeństwa — nie zmieniać na markę |
| `--body-bg` | `#f4f3fa` | = `--bg` frontendu |
| `--border-color`, `--hairline-color` | `#e3e1f0` | = `--border` frontendu |
| Kropki statusu (`blog/admin.py::_STATUS_COLORS`, ikonki `branding/admin.py`) | **bez zmian** | Już zatwierdzone, tekst zawsze towarzyszy kolorowi — nie dotykać |

**Teal (`#2e8b90`) — tylko akcent, nie tekst**: teal na białym tle daje
4.03:1, **nie przechodzi AA** (próg 4.5:1) dla normalnego tekstu/linków.
Używać wyłącznie jako dekoracja bez tekstu (dolna linia pod headerem,
obrys focus na polach formularza, mały pasek przy aktywnej zakładce
językowej) — nigdy jako kolor linku/przycisku z tekstem.

**Strona główna — grupowanie i kolejność:** 1. „Treść" (`blog.Post`,
`about.AboutMe`) 2. „Branding" (`branding.SiteBranding`) 3. „Konfiguracja AI"
(`ai_content.AIProviderSettings`, `ai_content.PostGenerator` / „Post z AI")
4. „Konta" (`accounts.User`) — kolejność wg częstości codziennego użycia
przez redaktora (treść najczęściej, konta najrzadziej).

**Logo:** jeden blok brandingu (`{% block branding %}` w
`admin/base_site.html`, renderowany na każdej stronie **i** na stronie
logowania — to ten sam szablon). `height: 32px` w headerze standardowych
stron, `height: 56px` na stronie logowania (Django i tak powiększa `#header`
na `/login/` własnym CSS) — `alt="okowFormie"`.

**Dark mode: wyłączony (świadomie), nie dziedziczony z Django.** CSS
override w `:root { ... }` **bez** owijania w
`@media (prefers-color-scheme: dark)` — nasz plik ładuje się po
`admin/css/base.css`, więc bezwarunkowe `:root` wygrywa z dark-mode blokiem
Django niezależnie od ustawień systemowych użytkownika. Dopasowanie
osobnej palety pod dark mode to dodatkowa praca projektowa poza zakresem
tego taska (do rozważenia jako follow-up, jeśli ktoś zgłosi potrzebę).

**Rozmiary widgetów (finalne wartości):**
- `meta_title` (blog **i** about): `forms.TextInput(attrs={"size": 80})` —
  jedna linia, wzorzec `cover_image_alt`/`photo_alt`.
- `meta_description` (blog **i** about): `forms.Textarea(attrs={"rows": 3})`
  — wzorzec `excerpt`.
- `extra_instructions` (`ai_content/admin.py::AIProviderSettingsAdmin`):
  `rows` `4` → `8`.
- `topic` (`ai_content/forms.py::PostGenerationForm`):
  `widget=forms.TextInput(attrs={"size": 60})`.
- `local_focus`: bez zmian (krótka nazwa miejsca, obecna szerokość wystarcza).

**Filtry/search — jedyny realny gap:** `PostAdmin.search_fields` nie
przeszukuje autora — dopisać `"author__username"` do istniejącego tuple.
Reszta (`TranslationCompletenessFilter`, `translations__status`, `author`,
`created_at`, `date_hierarchy`) już wystarczająca, bez zmian. Stockowy
`UserAdmin` (accounts) — domyślne filtry/`search_fields` Django już
wystarczające, bez zmian.

### Implementacja (krok 2 planu, backend-agent)

**Gdzie wylądował `AdminSite`/branding:**
- `backend/src/backend/admin.py` (nowy plik) — `admin.site.site_header` /
  `site_title` / `index_title`, plus `OkowformieAdminSite(admin.AdminSite)`
  z nadpisanym `get_app_list`. Przypisany na już istniejący singleton
  (`admin.site.__class__ = OkowformieAdminSite`), **nie** nowa instancja —
  każda domenowa apka rejestruje modele przez `@admin.register` na tym
  jednym, globalnym `admin.site`; nowa instancja zerowałaby rejestr, gdyby
  ten moduł zaimportował się po tamtych rejestracjach (kolejność importu
  apek w drugą stronę nie jest gwarantowana).
- `get_app_list` woła `self._build_app_dict(request, app_label)` (metoda
  Django) i tylko przekłada już przefiltrowany wynik (uprawnienia per
  model już rozstrzygnięte przez `has_module_permission`/
  `get_model_perms`) na kategorie ze specu — nigdy nie odpytuje ORM-u ani
  rejestru adminów od nowa. Zweryfikowane manualnie (Django test client,
  `docker compose exec backend`): superuser widzi kategorie w kolejności
  Treść/Branding/Konfiguracja AI/Konta; staff z samymi uprawnieniami
  `blog.*` widzi tylko „Treść” i „Konfiguracja AI” (bo `PostGeneratorAdmin.
  has_module_permission` już dziś opiera się na `blog.add_post`+
  `blog.change_post`, nie na uprawnieniach `ai_content` — to jest istniejące
  zachowanie z `ai_content/admin.py`, nie coś wprowadzonego tym taskiem);
  `AIProviderSettings` w tym przypadku poprawnie niewidoczny.
- `admin.site.get_app_list` wpływa też na sidebar nawigacji widoczny na
  **każdej** stronie panelu (`AdminSite.each_context` woła `get_app_list`
  bez `app_label`, wynik idzie do `admin/nav_sidebar.html`), nie tylko na
  stronę główną — to ten sam mechanizm Django, nie da się rozdzielić bez
  duplikowania logiki grupowania. Uznane za pozytywny efekt uboczny
  (konsekwentne grupowanie w całym panelu), nie regresję.
- `backend/src/backend/urls.py` importuje `backend.admin` jawnie (linia
  obok `admin.site.urls`) — `django.contrib.admin`'s `autodiscover()`
  znalazłby ten plik sam (każda apka w `INSTALLED_APPS` z `admin.py` jest
  automatycznie importowana), import jest tu tylko dla czytelności/
  odkrywalności zależności bez znajomości tego mechanizmu Django.

**Gdzie jest CSS/logo:**
- `backend/src/backend/static/admin/img/logo.png` — kopia
  `frontend/public/brand/logo.png` (plik ma rozszerzenie `.png`, ale to w
  rzeczywistości dane JPEG — tak samo jak w źródle we `frontend`; nie
  naprawiane w tym tasku, poza zakresem).
- `backend/src/backend/static/admin/css/okowformie-admin.css` — zmienne z
  tabeli wyżej, plus dwa doprecyzowania nieopisane w tabeli kolorów (patrz
  „Odstępstwa” niżej).
- `backend/src/backend/templates/admin/base_site.html` — nadpisuje blok
  `branding` (logo + `site_header`, ten sam blok renderuje się też na
  `/login/`) i `extrastyle` (dołącza CSS przez `{% static %}` +
  `{% csp_nonce_attr %}`, ten sam wzorzec co pliki CSS Django). Znaleziony
  automatycznie przez `APP_DIRS` (apka `backend` jest pierwsza w
  `INSTALLED_APPS`, przed `django.contrib.admin`) i przez
  `AppDirectoriesFinder` dla statyków — bez zmian w `TEMPLATES`/
  `STATICFILES_FINDERS` w `settings.py`. Potwierdzone: `collectstatic
  --dry-run -v2` widzi oba nowe pliki statyczne.

**Odstępstwa od specu (z uzasadnieniem):**
1. **`html[data-theme="dark"]` dopisany obok `:root`.** Spec mówił
   "bezwarunkowy `:root`, bez `@media (prefers-color-scheme: dark)`" — to
   wystarcza na automatyczny dark mode systemu, ale Django 6.1 ma
   DRUGI mechanizm dark mode: ręczny przełącznik w headerze
   (`admin/color_theme_toggle.html`), który ustawia atrybut
   `data-theme="dark"` na `<html>`. Ten selektor ma WYŻSZĄ specyficzność
   niż plain `:root` (atrybut na elemencie vs. pseudo-klasa), więc
   wygrałby z naszym nadpisaniem niezależnie od kolejności w źródle. Bez
   dopisania tego selektora "dark mode wyłączony" byłoby prawdą tylko dla
   automatycznego dark mode, nie dla ręcznego przełącznika — dopisany,
   żeby zrealizować literalną intencję specu, nie tylko jego dosłowne
   brzmienie o `:root`.
2. **Dodatkowa reguła `#site-name a:link, a:visited { color:
   var(--header-branding-color); }`.** Tabela kolorów specu mówi
   `--header-branding-color: #ffffff`, ale `admin/css/base.css` koloruje
   link nagłówka wprost z `var(--accent)` (żółty), nie z
   `--header-branding-color` — bez tej dodatkowej reguły tekst
   "okowFormie — Panel redakcyjny" zostałby żółty na granatowym tle,
   wbrew uzasadnieniu specu ("biały tekst na navy → 13.7:1"). Świadomie
   NIE nadpisany `--accent` samodzielnie: ten token steruje też tłem
   nagłówka kalendarza w widgecie daty (`admin/css/widgets.css`) ze stałym
   ciemnym tekstem (`#333`) — podmiana `--accent` na indygo dałaby tam
   nowy problem kontrastu, poza zakresem tego taska.
3. **`Certificate.issuer` help_text wymagał migracji.** `help_text` jest
   częścią `deconstruct()` pola Django — `makemigrations` wykrywa zmianę i
   generuje `AlterField` (`about/migrations/0002_alter_certificate_issuer.py`).
   Migracja jest metadanych: nie zmienia typu/ograniczeń kolumny w
   Postgresie, w pełni odwracalna, bez migracji danych — zgodna z
   „Migracje małe i odwracalne” (`.claude/rules/conventions.md`), nie
   wymaga zatrzymania się i pytania z `engineering-principles.md` (to
   dotyczy migracji **wymagającej migracji danych**, nie tej). Zastosowana
   lokalnie (`manage.py migrate about`).

**Znalezisko poza zakresem (dopisane do `docs/todo/TODO.md`):** repo ma
pre-existing rozjazd między `ruff check` (czysty) i `ruff format --check`
(8 plików niesformatowanych kanonicznie wg aktualnej wersji `ruff`,
niezwiązanych z tym taskiem: `about/admin.py`, `about/tests/test_models.py`,
`ai_content/admin.py`, `ai_content/models.py`,
`backend/management/commands/seed_demo_data.py`, `branding/admin.py`,
`core/tests/test_api.py`) — nienaprawiane tutaj (poza zakresem, dotyczy
całych plików, nie linii zmienionych tym taskiem).

**Weryfikacja:** `ruff check .` czysty, `mypy src` czysty (122 plików),
`manage.py check` czysty, `makemigrations --check --dry-run` czysty (po
wygenerowaniu migracji wyżej), `pytest` — 276 passed (uwaga: uruchamiane
przez `docker compose exec backend`, bo lokalny Postgres/Redis nie są
wystawione na hosta — `docker-compose.yml` — z jawnym
`OTEL_METRICS_ENABLED=False` w `exec`, bo długo działający kontener
`backend` ma tę zmienną `True` z `docker-compose.yml`, co fałszywie wywala
dwa niezwiązane testy telemetrii przy odpalaniu przez `exec` na już
działającym kontenerze). Testy jednostkowe dla `get_app_list`/grupowania
strony głównej pozostają w zakresie kroku **qa-agent** (plan wyżej) — ten
krok zweryfikował zachowanie manualnie (Django test client, opisane wyżej)
jako dowód przed oddaniem, nie jako zamiennik automatycznego testu.

### Testy (krok 3 planu, qa-agent)

**14 nowych testów**, żaden istniejący nie wymagał zmiany asercji (backend-agent
nie zmieniał zachowania, na którym istniejące testy już się opierały) —
`pytest` 276 → **290 passed**. `ruff check .` czysty, `mypy src` czysty (123
plików — +1 nowy plik testowy), `manage.py check` czysty, `makemigrations
--check --dry-run` czysty. Wszystko uruchamiane przez `docker compose exec
-e OTEL_METRICS_ENABLED=False backend uv run ...` (kontener już działał z
`docker compose up -d` z poprzedniej sesji).

- `backend/src/backend/tests/test_admin_site.py` (nowy, 7 testów) —
  `OkowformieAdminSite.get_app_list`: kolejność i skład kategorii dla
  superusera; **dwa** scenariusze filtrowania per uprawnienia (staff z samym
  `blog.add_post`+`blog.change_post` widzi tylko „Treść”+„Konfiguracja AI”,
  bez `AboutMe`/`AIProviderSettings`; staff z samym `accounts.view_user`
  widzi wyłącznie „Konta” — dwa różne przekroje uprawnień, nie tylko jeden,
  żeby dowieść, że filtrowanie nie jest przypadkowe dla jednej apki); staff
  bez żadnych uprawnień widzi listę pustą (nie samą płaską, nieprzefiltrowaną
  listę). Plus render: strona logowania i strona główna mają `site_header`,
  link do `okowformie-admin.css` i `admin/img/logo.png` w treści odpowiedzi.
- `blog/tests/test_admin.py` — `search_fields` z `author__username`: post
  wyszukany fragmentem nazwy autora (`"aktork"` z `"redaktorka"`) jest na
  liście, post innego autora (`"maria-nowak"`, celowo bez współdzielonego
  podciągu z `"redaktorka"`) nie jest — dowód zawężenia wyniku, nie tylko
  obecności w konfiguracji.
- `about/tests/test_models.py` — `Certificate.issuer` ma niepusty `help_text`.
- `ai_content/tests/test_forms.py` (+2) — `topic`/`local_focus` mają niepusty
  `help_text`; `topic` ma `TextInput(size=60)`.
- `blog/tests/test_admin_form.py`, `about/tests/test_admin_form.py` (+1
  każdy) — `meta_title`/`meta_description` mają powiększone widgety
  (`size=80`/`rows=3`) w obu formularzach.
- `ai_content/tests/test_admin.py` (+1) — `extra_instructions` ma
  `Textarea(rows=8)` przez `AIProviderSettingsAdmin.get_form()`.

**Znalezisko poza zakresem (dopisane do `docs/todo/TODO.md`):**
`{% csp_nonce_attr %}` w `base_site.html:20` (Django 6.1 wbudowany tag CSP)
renderuje zawsze pusty string — `settings.py` nie ma ani
`ContentSecurityPolicyMiddleware`, ani `SECURE_CSP`, więc w kontekście
requestu nigdy nie ma nonce'u do wstawienia. Nie regresja tego taska
(backend-agent nie dotykał `settings.py`, a użycie tagu jest poprawnym
wzorcem "gdyby CSP kiedyś włączono") — pre-existing gap względem
`.claude/rules/security.md` (CSP wymagane jako nagłówek bezpieczeństwa),
tylko zauważony przy tym review. Nienaprawiane tutaj — poza zakresem
qa-agenta (edytuje wyłącznie katalogi testów) i poza zakresem tego taska.

**Żadnego innego defektu w kodzie backend-agenta nie znaleziono** — logika
`get_app_list` (filtrowanie przez `_build_app_dict`, bez ponownego
odpytywania rejestru/ORM-u), przypisanie `admin.site.__class__` na singleton,
oba odstępstwa od specu CSS (`data-theme="dark"`, `#site-name a` kolor) są
uzasadnione i zweryfikowane działają zgodnie z opisem. Werdykt: **GO** —
`/code-review` (medium) po tym kroku również bez znalezisk.

### Defekt zgłoszony przez użytkownika po `/check`+`/code-review`: "białe kolory się nakładają"

Zgłoszenie przyszło **po** zielonym `/check` i czystym `/code-review` —
żaden z automatycznych testów (`qa-agent`) tego nie wychwycił, bo problem
ujawnia się tylko pod konkretnym stanem przeglądarki/systemu (dark mode),
którego żaden test nie symulował.

**Diagnoza (zweryfikowana w kodzie Django, nie zgadywana):**
`admin/css/dark_mode.css` Django definiuje **pełny** zestaw zmiennych CSS na
dark mode (`--body-fg`, `--breadcrumbs-*`, `--primary-fg`, `--darkened-bg`
itd.) w dwóch miejscach: `@media (prefers-color-scheme: dark) { :root {...} }`
(automatyczny, wg systemu) i `html[data-theme="dark"] { ... }` (ręczny
przełącznik w headerze). `okowformie-admin.css` (pierwsza wersja)
nadpisywał tylko **część** tych zmiennych (`--header-bg`, `--body-bg`,
`--link-fg`... — patrz tabela wyżej), nie `--body-fg`. Efekt: przy
systemowym dark mode **albo** ręcznym przełączniku, `--body-fg` zostawał
jasny (`#eeeeee`, z `dark_mode.css`) a `--body-bg` **też** jasny (`#f4f3fa`,
z naszego pliku) — jasny tekst na jasnym tle, dokładnie zgłoszony objaw.
Odstępstwo #1 z sekcji wyżej (`html[data-theme="dark"]` dopisany obok
`:root`) rozwiązywało tylko **specyficzność wygrywającego selektora**, nie
**kompletność** listy nadpisywanych zmiennych — literalnie zrealizowany
spec ("dark mode wyłączony"), ale niekompletnie, bo enumerowanie każdej
zmiennej Django do nadpisania jest z natury kruche (nowa wersja Django może
dodać kolejne).

**Naprawa (bardziej odporna, nie łatanie kolejnych zmiennych):**
Całkowite usunięcie mechanizmu dark mode Django z HTML, nie tylko
nadpisanie jego zmiennych:
- `admin/base_site.html` — nowy `{% block dark-mode-vars %}{% endblock %}`
  (pusty) usuwa `<link admin/css/dark_mode.css>` i
  `<script admin/js/theme.js>` z `<head>` — te zmienne CSS nigdy nie
  powstają, niezależnie od systemu użytkownika.
- `admin/color_theme_toggle.html` (nowy plik, nadpisanie na pusty) — usuwa
  przycisk przełącznika z headera (dla zalogowanych) i ze strony logowania;
  bez `theme.js` byłby niefunkcjonalnym przyciskiem.
- Efekt: `data-theme` nigdy nie jest ustawiane przez nic w tym panelu, więc
  odstępstwo #1 (`html[data-theme="dark"]` w CSS) stało się zbędne —
  usunięte, `okowformie-admin.css` wraca do plain `:root { ... }`.
- **Defekt wtórny znaleziony przy naprawie**: pierwsza wersja obu nowych
  szablonów użyła wielolinijkowego komentarza Django `{# ... #}` — w tej
  wersji Django (6.1) taka składnia **nie** jest parsowana jako komentarz i
  renderuje się jako zwykły tekst w HTML (potwierdzone: tekst komentarza z
  `color_theme_toggle.html` pojawiał się w treści strony, obok przycisku
  "Wyloguj się"). Naprawione na `{% comment %}...{% endcomment %}`
  (dokumentowana, wieloliniowa składnia Django) w obu plikach.
- **Test regresji dopisany** (`backend/tests/test_admin_site.py`, +2):
  `test_strona_logowania_nie_laduje_dark_mode_django` /
  `test_strona_glowna_panelu_nie_laduje_dark_mode_django` — asercja, że
  `dark_mode.css`/`theme.js`/`theme-toggle` nie występują w treści
  odpowiedzi, na obu stronach.

**Weryfikacja po naprawie:** `ruff check .` czysty, `mypy src` czysty,
`pytest` **292 passed** (290 + 2 nowe testy regresji), `manage.py check`
czysty. Zweryfikowane też bezpośrednio (Django test client): strona
logowania nie zawiera `dark_mode.css`/`theme.js`/`theme-toggle`, zawiera
`okowformie-admin.css`/logo/`site_header`.

Do zamknięcia taska pozostaje: potwierdzenie **wizualne** przez użytkownika
w rzeczywistej przeglądarce (brak dostępu do przeglądarki w tym
środowisku), zwłaszcza że pierwotne zgłoszenie było wizualne, nie z testu
automatycznego.

### Drugie zgłoszenie użytkownika (po naprawie dark mode): "wszystko się zlewa"

Po naprawie dark mode użytkownik zgłosił kolejny wizualny problem: pola
formularza nie odznaczają się od tła. Diagnoza w kodzie (bez zgadywania):
`--border-color` (obramowanie `<input>`/`<textarea>`/`<select>`,
`admin/css/forms.css`) i `--hairline-color` (linie działowe w `.module`,
`admin/css/base.css`) w pierwszej wersji `okowformie-admin.css` miały tę
samą wartość co `--body-bg` (`#e3e1f0` ≈ `#f4f3fa`, kontrast ~1:1) — pola
formularza wizualnie zlewały się z tłem strony.

**Naprawa:** `--border-color: #8a869c` (kontrast do `--body-bg` policzony
programowo: **3.19:1**, przechodzi próg WCAG 1.4.11 dla granic elementów
UI, ≥3:1), `--hairline-color: #c9c6da` (**1.51:1** — świadomie subtelniejsze,
ten sam stosunek "border ciemniejszy niż hairline" co w domyślnym Django
`#ccc`/`#e8e8e8`). Czysto CSS, zero zmian Pythona — `pytest` (podzbiór
`backend/tests`) 12/12 bez zmian po edycji.

Wciąż otwarte: wizualne potwierdzenie przez użytkownika w przeglądarce —
oba zgłoszenia były wizualne, żaden automatyczny test w tym repo nie
renderuje realnego CSS w przeglądarce (brak takiego narzędzia w tym
środowisku).
