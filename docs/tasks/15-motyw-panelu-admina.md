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
- [ ] **backend-agent** — implementacja wg spec:
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
- [ ] **qa-agent** — testy: render strony głównej panelu (kategorie w
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
