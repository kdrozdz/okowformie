# To-do

Format i statusy: `README.md` w tym folderze.

## [otwarte] Liczenie unikalnych odwiedzających bloga — osobny task, poza OTel/Prometheus (2026-09-22)
Przy tasku 14 (observability) padło pytanie "ile osób dziś odwiedziło stronę".
Prometheus/OTel liczy requesty, nie unikalnych użytkowników — etykietowanie
metryk po IP/sesji powoduje eksplozję kardynalności, Prometheus nie jest do
tego zaprojektowany. Świadomie odłożone: potrzebne osobne narzędzie web
analytics (np. self-hosted Umami/Plausible albo GA), inny problem niż infra
health mierzona w tasku 14. Do zrobienia dopiero na jawne zlecenie.

**Kontekst:** `docs/decisions/2026-09-22-observability-otel-prometheus.md`
(sekcja Alternatywy), `docs/tasks/14-observability-otel-prometheus.md`.

## [otwarte] `docker compose exec backend python manage.py <cokolwiek>` koliduje z portem metryk, gdy `backend` już działa (2026-09-22)
`docker-compose.yml` ustawia `OTEL_METRICS_ENABLED: ${OTEL_METRICS_ENABLED:-True}` na poziomie **kontenera** `backend` (zgodnie z planem taska 14, sekcja 4) — dotyczy więc każdego procesu `manage.py` uruchomionego w tym kontenerze, nie tylko głównego `runserver`. Guard `is_runserver_reload_watcher` w `core/telemetry.py` (dodany w tym samym tasku) rozwiązuje kolizję portu 9464 między procesem-rodzicem i dzieckiem autoreloadera `runserver`, ale **nie** chroni przed kolizją, gdy deweloper odpali dodatkową komendę w już działającym kontenerze, np. `docker compose exec backend python manage.py shell` — ten nowy proces też ma `OTEL_METRICS_ENABLED=True`, nie jest `runserver`, więc `setup_telemetry()` próbuje ponownie zbindować port 9464 zajęty już przez główny proces serwera i pada `OSError: Address already in use` (zweryfikowane empirycznie przy weryfikacji end-to-end taska 14). `docker compose exec backend python manage.py migrate`/`createsuperuser`/`test` mają ten sam problem. **Ten sam błąd łapie też `mypy`** — `django-stubs`/`mypy_django_plugin` woła `django.setup()` wewnętrznie przy starcie, więc `docker compose exec backend mypy src` (jedna z komend `/check`) pada identycznym `OSError: Address already in use`, jeśli kontener `backend` już działa (zweryfikowane empirycznie przy weryfikacji end-to-end taska 14 — `mypy src` bez obejścia kończy się `INTERNAL ERROR`, z `-e OTEL_METRICS_ENABLED=False` przechodzi czysto). Obejście na teraz: `docker compose exec -e OTEL_METRICS_ENABLED=False backend python manage.py shell` / `... mypy src` (nadpisanie zmiennej per-exec). Do rozważenia przy rewizji: guard szerszy niż tylko `runserver` (np. `OTEL_METRICS_ENABLED` faktycznie `True` tylko dla procesu nasłuchującego na `0.0.0.0:8000`, nie dla każdej komendy), albo osobna zmienna typu `OTEL_METRICS_STANDALONE_PROCESS` do jawnego wyłączania w jednorazowych execach — powiązane z już opisaną niżej kolizją portu przy gunicornie (ten sam korzeń: `start_http_server()` bez świadomości wielu procesów).

**Kontekst:** `backend/src/core/telemetry.py` (`is_runserver_reload_watcher`), `docker-compose.yml`
(`OTEL_METRICS_ENABLED` w `environment:` usługi `backend`), `docs/tasks/14-observability-otel-prometheus.md`
sekcja 5 (weryfikacja end-to-end).

## [zrobione] `PsycopgInstrumentor` nie emitował żadnych metryk Prometheusa — zastąpiony własnym middleware DB (2026-09-22)
Task 14 (decyzja `docs/decisions/2026-09-22-observability-otel-prometheus.md`) zakładał metryki DB
(Postgres/psycopg) na backendzie "przez gotowe pakiety auto-instrumentacji OTel" —
zweryfikowane empirycznie przy weryfikacji end-to-end (sekcja 5), że to **nie działa**:
`opentelemetry-instrumentation-psycopg` (`_instrument()`, zbadane bezpośrednio w źródle
zainstalowanego pakietu) integruje się wyłącznie przez `tracer_provider`/`_get_tracer()` — nie ma
żadnej ścieżki metryk. Task 14 świadomie **nie** konfiguruje `TracerProvider`/eksportera trace'ów
(decyzja: "błędy jako metryki, nie logi/traces") — więc ta instrumentacja faktycznie nie produkowała
żadnych obserwowalnych danych: `/metrics` na `backend:9464` nie zawierało ani jednej serii związanej z
DB, niezależnie od realnego ruchu. `.instrument()` samo w sobie się nie wywalało (brak błędu, kod
"działał"), więc łatwo to było przeoczyć bez ręcznej weryfikacji zawartości `/metrics`.

**Naprawione** (sekcja 1a planu taska 14): `PsycopgInstrumentor` usunięty (`uv remove
opentelemetry-instrumentation-psycopg`), zastąpiony własnym middleware
`core.telemetry.DBQueryMetricsMiddleware` — owija `connection.execute_wrapper` (wbudowany hak Django),
histogram `django_db_query_duration_seconds` z etykietą `operation`. Zweryfikowane realnym ruchem po
`docker compose up -d --build backend`: `django_db_query_duration_seconds_count{operation="SELECT"}`
rośnie z ruchem, `_sum` niezerowy.

**Redis pozostaje poza zakresem — świadoma decyzja, nie znalezisko do naprawy.**
`RedisInstrumentor` miał ten sam defekt (no-op bez `TracerProvider`) i został usunięty razem z
psycopg (`uv remove opentelemetry-instrumentation-redis`), ale nie dostał odpowiednika
`execute_wrapper` — nie było to zlecone, a `redis-py` nie ma analogicznego wbudowanego haka (wymagałoby
ręcznego owijania klienta). Jeśli metryki cache staną się potrzebne, to osobny, świadomie zlecony task.

**Kontekst:** `backend/src/core/telemetry.py` (`DBQueryMetricsMiddleware`, `_record_db_query`),
`docs/decisions/2026-09-22-observability-otel-prometheus.md` (punkt "Zestaw metryk"),
`docs/tasks/14-observability-otel-prometheus.md` sekcja 1a.

## [otwarte] Prometheus + gunicorn multi-worker: kolizja portu metryk w produkcji (2026-09-22)
Python `opentelemetry-exporter-prometheus` (`PrometheusMetricReader`) nie
stawia własnego serwera HTTP — wymaga ręcznego `prometheus_client.start_http_server()`
w procesie. Zaimplementowane w tasku 14 pod `runserver` (dev, jeden proces) —
działa. `backend/Dockerfile` w produkcji odpala gunicorn z `--workers 3`:
3 procesy próbujące zbindować ten sam port `9464` się wysypią. Nierozwiązane
świadomie — task 14 ma scope tylko dev (patrz decyzja). Do podjęcia przy
tasku deployu produkcyjnego na Cyberfolks VPS — rozwiązania: prometheus_client
multiprocess mode (`PROMETHEUS_MULTIPROC_DIR`) albo przejście na wariant z
OTel Collectorem (patrz alternatywy w decyzji) zbierającym OTLP z workerów.

**Kontekst:** `docs/decisions/2026-09-22-observability-otel-prometheus.md`,
`backend/Dockerfile` (`--workers 3`).

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

## [otwarte] Wersjonowanie system promptów generatora AI (2026-09-20)
Padł pomysł, żeby wersjonować konfigurację/prompt generatora postów AI
(`AIProviderSettings`, w tym pole `extra_instructions`) — np. żeby wiedzieć,
z jaką dokładnie wersją promptu powstał dany post, albo móc wrócić do
poprzedniej wersji instrukcji. Częściowo to już działa za darmo: Django
Admin loguje każdą zmianę zapisaną przez panel (`django.contrib.admin.models.LogEntry`,
link „Historia” na formularzu edycji) — kto, kiedy, które pole zmienił w
„Ustawieniach AI”. Czego to nie daje: powiązania konkretnego wygenerowanego
posta z dokładną wersją promptu, która go stworzyła — `Post`/`PostTranslation`
świadomie nie mają żadnych pól o AI (decyzja #8 w `docs/tasks/12-generator-postow-ai.md`,
celowo, żeby blog zostawał czysty niezależnie od tego, czy generator kiedyś
zniknie). Świadomie nierozwinięte teraz — funkcja jeszcze nieużywana, brak
realnej potrzeby do zweryfikowania. Do decyzji przy rewizji: albo zbudować
(osobny log w `ai_content` linkujący do posta, bez zmiany schematu `blog`),
albo świadomie odrzucić ten pomysł.

**Kontekst:** `docs/tasks/12-generator-postow-ai.md`, rozmowa po sekcji 5a
(edytowalne instrukcje dla AI).

## [otwarte] Rezydualne ryzyko: SDK dostawcy AI mógłby wpisać fragment klucza API do treści wyjątku (2026-09-20)
`ai_content/services.py::generate_post_content` łapie `Exception` szeroko i
loguje pełny traceback przez `logger.exception(...)` (do logu serwera, nigdy
do usera — to działa poprawnie, zweryfikowane testem). Teoretyczne,
niezweryfikowane ryzyko: gdyby SDK dostawcy (`langchain-anthropic`/
`langchain-openai`/`langchain-xai`) kiedyś zwrócił błąd uwierzytelnienia z
fragmentem klucza w treści wyjątku (np. echo nagłówka `Authorization`), ten
fragment wylądowałby w logu serwera. Nie znaleziono takiego zachowania w
kodzie `ai_content` — źródłem musiałaby być biblioteka trzecia, czego nie da
się zweryfikować bez realnego wywołania z błędnym kluczem. Do rozważenia:
log-scrubbing filter na loggerze `ai_content.services`, albo jednorazowy
manualny test z celowo błędnym kluczem przed pierwszym produkcyjnym użyciem.

**Kontekst:** `docs/tasks/12-generator-postow-ai.md`, niezależne review
`qa-agent` (sekcja 6, Defekt #2, informational/low).

## [zrobione] Domyślne granice bucketów histogramu `django_db_query_duration_seconds` niedopasowane do jednostki (sekundy vs milisekundy) — p95 mylący (2026-09-22)
Przy dokładaniu panelu "DB query latency p95" do `http-overview.json` (task 14,
uzupełnienie po sekcji 1a) zweryfikowane empirycznie przez datasource proxy
Grafany: `histogram_quantile(0.95, sum by (operation, le) (rate(django_db_query_duration_seconds_bucket{job="backend"}[5m])))`
zwraca `4.75` (sekund) dla ruchu, gdzie realny `_sum`/`_count` daje średnio
~1.1ms na zapytanie (`_sum=0.166`, `_count=150`). Przyczyna: `meter.create_histogram(...)`
w `core/telemetry.py` (sekcja 1a) nie ustawia jawnych `explicit_bucket_boundaries`
— OTel SDK Python używa domyślnych granic `[0, 5, 10, 25, 50, 75, 100, 250,
500, 750, 1000, 2500, 5000, 7500, 10000]`, zaprojektowanych pod **milisekundy**,
podczas gdy metryka jest w **sekundach** (`unit="s"`, `duration =
time.perf_counter() - start` bez konwersji). Efekt: prawie wszystkie zapytania
(rzędu milisekund) trafiają do pierwszego niezerowego bucketu `le=5.0`
(czyli "≤5 sekund"), więc `histogram_quantile` interpoluje liniowo między 0 a
5s i zwraca wartości rzędu sekund zamiast milisekund — panel istnieje i
zwraca niepuste dane (zgodnie z zakresem uzupełnienia), ale liczby są
praktycznie bezużyteczne do realnej oceny p95. Nie naprawione w tym
uzupełnieniu — wymagałoby zmiany `backend/src/core/telemetry.py`
(`View(aggregation=ExplicitBucketHistogramAggregation([...]))` z granicami
rzędu ułamków sekundy, np. `[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5,
1, 2.5, 5]`), poza zakresem infra-agenta (`backend/` nie w jego katalogach).

**Kontekst:** `infra/grafana/provisioning/dashboards/http-overview.json`
(panel "DB query latency p95"), `backend/src/core/telemetry.py`
(`django_db_query_duration_seconds`, sekcja 1a), `docs/tasks/14-observability-otel-prometheus.md`.

**Fix:** `backend/src/core/telemetry.py` — `MeterProvider` dostaje `views=[View(instrument_name="django_db_query_duration_seconds", aggregation=ExplicitBucketHistogramAggregation(boundaries=(0.0005, 0.001, 0.0025, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5)))]`
(w sekundach, dopasowane do realnej skali ~1ms/zapytanie z marginesem do 5s).
`View`/`ExplicitBucketHistogramAggregation` importowane z `opentelemetry.sdk.metrics.view`
(nie z `opentelemetry.sdk.metrics` jak w pierwotnym szkicu znaleziska — zweryfikowane
bezpośrednio w zainstalowanej wersji SDK). Szczegóły weryfikacji i wynik przed/po:
`docs/tasks/14-observability-otel-prometheus.md`, sekcja "Decyzje po drodze".

## [otwarte] `ruff format --check` niesformatowany na 8 plikach, niezwiązanych z żadnym bieżącym taskiem (2026-09-23)
Przy weryfikacji taska 15 (motyw panelu admina) `ruff check .` jest czysty,
ale `ruff format --check .` zgłasza 8 plików wymagających reformatowania —
żaden z nich nie jest plikiem, który ten task dotykał merytorycznie (poza
jedną linią w `ai_content/admin.py`, gdzie diff ograniczony do faktycznej
zmiany, formatowanie reszty pliku pozostało nienaruszone świadomie, patrz
`docs/tasks/15-motyw-panelu-admina.md`). Lista: `about/admin.py`,
`about/tests/test_models.py`, `ai_content/admin.py`, `ai_content/models.py`,
`backend/management/commands/seed_demo_data.py`, `branding/admin.py`,
`core/tests/test_api.py`. Najpewniej drift między wersją `ruff` użytą przy
pisaniu tego kodu i wersją aktualnie zainstalowaną (`pyproject.toml`:
`ruff>=0.16.8`, bez pinowania konkretnej wersji formatującej). `/check` nie
wywołuje `ruff format --check` (tylko `ruff check`), więc to nie blokuje
merge, ale drift będzie rósł przy każdym kolejnym tasku, jeśli nikt tego nie
ujednolici jednym, świadomym commitem `ruff format .` na całym repo.

**Kontekst:** `docs/tasks/15-motyw-panelu-admina.md`, sekcja "Decyzje po
drodze" → "Implementacja (krok 2 planu, backend-agent)".

## [otwarte] Synchroniczne wywołanie LLM w generatorze postów może blokować worker gunicorna produkcyjnego (2026-09-21)
`ai_content/services.py::generate_post_content` woła LLM synchronicznie
(do 60s timeout) wewnątrz widoku admina — świadoma decyzja #7 w
`docs/tasks/12-generator-postow-ai.md` (bez Celery/kolejki, YAGNI, jedna
osoba, okazjonalne użycie). `backend/Dockerfile` uruchamia produkcyjnie
`gunicorn --workers 3` — ten sam pool workerów obsługuje panel admina i
publiczny blog/API. Jedno kliknięcie „Wygeneruj” może zająć worker na do
60s; przy 3 workerach to ok. 1/3 całej pojemności serwowania, więc
odwiedzający stronę w tym oknie czasowym ma realną szansę na podwyższone
opóźnienie albo timeout. Znalezisko z `/code-review medium` — nie
naprawiane teraz (fix wymagałby kolejki/async, czyli cofnięcia świadomej
decyzji #7), ale warto to sprawdzić, jeśli funkcja zacznie być używana
częściej niż okazjonalnie, albo przy skalowaniu liczby workerów.

**Kontekst:** `docs/tasks/12-generator-postow-ai.md`, `/code-review medium`
na branchu `12-generator-postow-ai`, `backend/Dockerfile` (`--workers 3`).

## [otwarte] `{% csp_nonce_attr %}` w szablonach admina nie robi nic — brak CSP middleware/policy w `settings.py` (2026-09-23)
`backend/src/backend/templates/admin/base_site.html:20` dołącza
`okowformie-admin.css` przez `{% csp_nonce_attr %}` (Django 6.1 wbudowany
tag CSP, zweryfikowane w `django/utils/csp.py::nonce_attr` — nie wymaga
`{% load %}`, sam plik nie ma żadnej biblioteki niestandardowej). Tag
renderuje atrybut `nonce="..."` tylko wtedy, gdy w kontekście requestu jest
nonce, co dzieje się jedynie za `django.middleware.csp.
ContentSecurityPolicyMiddleware` z ustawionym `SECURE_CSP` — żadne z tych
dwóch nie istnieje w `backend/src/backend/settings.py` (zweryfikowane:
`grep -rn "SECURE_CSP\|ContentSecurityPolicyMiddleware"` bez wyniku). Efekt:
tag zawsze renderuje puste `""`, więc `<link>` do arkusza stylów admina
wygląda jak przygotowany pod CSP, ale w praktyce nie ma żadnej polityki CSP
chroniącej panel ani resztę serwisu — `.claude/rules/security.md` wymaga
nagłówków bezpieczeństwa (HSTS, CSP, X-Content-Type-Options,
Referrer-Policy, CSP bez `unsafe-inline`), a CSP konkretnie nie jest
wdrożone wcale. Nie jest to regresja taska 15 (backend-agent nie dotykał
`settings.py`, użycie tagu jest poprawnym wzorcem "gdyby CSP kiedyś
włączono") — pre-existing gap z wcześniejszych tasków, tylko zauważony przy
tym review. Do zrobienia: dodać `ContentSecurityPolicyMiddleware` +
`SECURE_CSP` do `MIDDLEWARE`/`settings.py` (dyrektywy `script-src`/
`style-src` z `'self'` + noncem, bez `unsafe-inline`), jako osobny task
bezpieczeństwa, nie doklejka do kolejnego niezwiązanego taska.

**Kontekst:** `backend/src/backend/templates/admin/base_site.html:20`,
`backend/src/backend/settings.py` (brak `SECURE_CSP`/
`ContentSecurityPolicyMiddleware` w `MIDDLEWARE`), `.claude/rules/security.md`,
`docs/tasks/15-motyw-panelu-admina.md`.

## [otwarte] `test_telemetry.py` failuje wewnątrz kontenera `backend`, bo `docker-compose.yml` ustawia `OTEL_METRICS_ENABLED: True` domyślnie (2026-09-23)
`uv run pytest` uruchomiony przez `docker compose exec backend` failuje na
`test_middleware_nie_wola_execute_wrapper_gdy_otel_wylaczony` i
`test_ready_nie_wola_setup_telemetry_gdy_flaga_wylaczona`
(`src/core/tests/test_telemetry.py`) — oba zakładają
`OTEL_METRICS_ENABLED=False`, ale `docker-compose.yml:101` ustawia
`OTEL_METRICS_ENABLED: ${OTEL_METRICS_ENABLED:-True}` jako domyślną wartość
dla usługi `backend`, więc `printenv OTEL_METRICS_ENABLED` w kontenerze
zwraca `True` i testy widzą realne wywołanie `setup_telemetry()`, którego
nie oczekują. Niezwiązane z `downloads` (taska 16) — zauważone tylko przy
uruchamianiu pełnego `uv run pytest` przez `docker compose exec` przy
weryfikacji tego taska; poza `core`/`downloads` nic nie zmieniono. Do
sprawdzenia: albo testy powinny same nadpisywać `OTEL_METRICS_ENABLED` przez
`override_settings`/`monkeypatch` zamiast zakładać wartość ze środowiska,
albo `docker-compose.yml` powinien mieć `OTEL_METRICS_ENABLED: False`
domyślnie dla usługi `backend` używanej też do testów (z osobnym profilem/
override dla obserwowalności, jeśli to ma zostać włączone celowo).

**Kontekst:** `backend/src/core/tests/test_telemetry.py`
(`test_middleware_nie_wola_execute_wrapper_gdy_otel_wylaczony`,
`test_ready_nie_wola_setup_telemetry_gdy_flaga_wylaczona`),
`docker-compose.yml:101`, `docs/tasks/16-pliki-do-pobrania.md` (znalezione
przy weryfikacji `uv run pytest` przez `docker compose exec backend`).
na branchu `12-generator-postow-ai`, `backend/Dockerfile` (`--workers 3`).
