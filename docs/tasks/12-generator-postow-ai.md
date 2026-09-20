# 12 — Generator postów przez AI (LangChain)

- **Cel:** Zakładka „Post with AI” w Django Admin — redaktor wpisuje temat, LangChain (Anthropic/OpenAI/Grok, wybierane w zakładce „AI model”) generuje treść ze structured output (Pydantic), backend tworzy z tego `Post` (draft, PL) i pokazuje link + uzasadnienie SEO.
- **Status:** plan implementacji gotowy (niżej). Branch `12-generator-postow-ai` utworzony z `dev`. Zero kodu, zero migracji — implementacja jeszcze nie rozpoczęta.

## Decyzje wejściowe

Kontekst i wcześniejsze ustalenia: `docs/decisions/2026-09-19-langchain-osobny-task.md` (pola generowane: `title`, `excerpt`, `content`, `meta_title`, `meta_description`, `cover_image_alt`; poza AI: `slug`, `author`, `status`, `published_at`, `updated_at`, `cover_image`; wynik zawsze ląduje jako `draft`).

Ustalone w tej sesji (rozmowa brainstormingowa — nieopisane jeszcze w kodzie):

1. **Nowa aplikacja `ai_content`** (nie wewnątrz `blog`) — importuje `blog.models.Post`/`PostTranslation`, żeby stworzyć wpis. `blog` zostaje wolny od zależności LangChain + 3 SDK providerów (odwrócenie zależności, `engineering-principles.md`). Nazwa do potwierdzenia przy implementacji, jeśli ktoś wymyśli lepszą.
2. **Konfiguracja providera — singleton** `AIProviderSettings` w `ai_content`, wzorowany 1:1 na `about.models.AboutMe` (`pk=1`, `has_add_permission` blokuje drugi rekord). Pola: `provider` (`anthropic`/`openai`/`xai`), `model_name` (tekst wolny, bez sztywnych `choices` — nazwy modeli zmieniają się częściej niż release kodu), `temperature`, `max_output_tokens`. Zakładka „AI model” w adminie edytuje ten jeden rekord.
3. **Klucze API — wyłącznie zmienne środowiskowe**, nazwane zgodnie z konwencją bibliotek LangChain: `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `XAI_API_KEY`. LangChain czyta je sam ze środowiska — klucz nigdy nie przechodzi przez kod Django, nie trafia do ustawień ani logów. Zgodne z `security.md`/`scope.md` (bez AWS, bez nowego narzędzia do sekretów). Otwartą pozycję w `CLAUDE.md` → „Otwarte decyzje” → „Sekrety bez AWS” można uznać za rozstrzygniętą tym wyborem — do przeniesienia do „Rozstrzygnięte” przy okazji implementacji.
4. **Generowanie: `init_chat_model(...).with_structured_output(GeneratedPostContent)`** (ujednolicone API LangChain, niezależne od providera). Pydantic `GeneratedPostContent`: `title`, `excerpt`, `content` (HTML ograniczony do tagów z `blog.models.POST_CONTENT_EXTENSIONS`), `meta_title`, `meta_description`, `cover_image_alt`, `seo_rationale` (uzasadnienie wyboru słów/SEO — **tylko** do komunikatu w adminie, nigdy do bazy).
5. **Fokus lokalny „Wrocław, Polska”** — edytowalne pole formularza (prefill „Wrocław, Polska”), wchodzi do system promptu. Nie jest hardkodowane w kodzie.
6. **AI generuje tylko wersję PL.** Tłumaczenie EN zostaje ręczne — poza zakresem tego taska.
7. **Widok „Post with AI”** — proxy-model bez własnej tabeli w DB, zarejestrowany w adminie (ten sam trik co `changelist_view` override w `AboutMeAdmin`, ale renderujący formularz zamiast redirectu/listy). Pola formularza: temat, fokus lokalny. Submit woła serwis generujący **synchronicznie** (bez Celery/kolejki — jedna osoba, okazjonalne użycie, YAGNI), w transakcji tworzy `Post` (`author=request.user`, `cover_image` puste — obrazek nadal wgrywa człowiek) + `PostTranslation` (`status=draft`), przekierowuje na edycję posta z komunikatem: link + `seo_rationale`.
8. **Uzasadnienie SEO nie jest persystowane** — tylko `messages.success` po stworzeniu posta. Zgodne z decyzją, że `Post` nie wymaga zmian schematu.
9. **Obsługa błędów** — brak klucza / timeout / błąd providera / nieudana walidacja Pydantic → komunikat po polsku, transakcja się nie zatwierdza, **żaden** `Post` nie powstaje.
10. **Testy** — unit: budowa promptu, mapowanie `GeneratedPostContent → Post/PostTranslation`, walidacja configu. Integration: widok admina z zamockowanym LLM (sukces + każda ścieżka błędu). Bez uderzania w realne API w CI.

## Plan

- [x] Wywołać skill `writing-plans` na bazie sekcji „Decyzje wejściowe” wyżej i rozpisać checklistę niżej.
- [x] Branch `12-generator-postow-ai` odbity z `dev`.

Wzorzec do naśladowania w każdym kroku: `about` (app analogiczna do `blog`, singleton `AboutMe` 1:1 z `AIProviderSettings` niżej — `about/models.py`, `about/admin.py`, `about/tests/test_admin.py`). Referencje pól: `blog/models.py` (`PostTranslation`, `POST_CONTENT_EXTENSIONS`), `blog/constants.py` (`Language`, `PostStatus`), `core/constants.py` (limity SEO).

### 1. Zależności i szkielet aplikacji
- [x] backend-agent: `cd backend && uv add langchain langchain-anthropic langchain-openai langchain-xai` — nowa zależność w stacku, już zaakceptowana przez ten task (`docs/decisions/2026-09-19-langchain-osobny-task.md`), więc bez dodatkowego pytania.
- [x] backend-agent: nowa aplikacja `backend/src/ai_content/` — `apps.py` (`AiContentConfig`, `name = "ai_content"`, `verbose_name = "Generator treści AI"`, wzorem `blog/apps.py`), `__init__.py`, `migrations/__init__.py`.
- [x] backend-agent: dopisać `"ai_content"` do `INSTALLED_APPS` w `backend/src/backend/settings.py`, w sekcji „Apps domenowe”, po `"about"`.
- [x] backend-agent: `backend/env.example` — nowa sekcja `# --- AI (generator postów) ---` dokumentująca `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `XAI_API_KEY` jako zmienne czytane **bezpośrednio przez LangChain** (zakomentowane, bez wartości, wzorem reszty pliku); komentarz wprost: klucz nigdy nie przechodzi przez kod/ustawienia Django.

### 2. Model i migracja
- [x] backend-agent: `ai_content/constants.py` — `AIProvider(models.TextChoices)`: `ANTHROPIC = "anthropic", "Anthropic (Claude)"`, `OPENAI = "openai", "OpenAI (GPT)"`, `XAI = "xai", "xAI (Grok)"`. Wartości identyczne ze stringami providera, jakich oczekuje `langchain.chat_models.init_chat_model(model_provider=...)` — świadomy wybór, nie przypadek.
- [x] backend-agent: `ai_content/models.py` — `AIProviderSettings(models.Model)` (zwykły model, **nie** `TranslatableModel` — konfiguracja jest niezależna od języka): `provider` (`CharField`, `choices=AIProvider`, `default=AIProvider.ANTHROPIC`), `model_name` (`CharField(max_length=100)`, bez `choices` — nazwy modeli zmieniają się częściej niż release kodu, `help_text` to tłumaczy), `temperature` (`FloatField(default=0.7, validators=[MinValueValidator(0), MaxValueValidator(2)])`), `max_output_tokens` (`PositiveIntegerField(default=4000, validators=[MinValueValidator(1)])`). Singleton 1:1 z `about.models.AboutMe`: `SINGLETON_ID: ClassVar[int] = 1`, `save()` wymusza `self.pk = SINGLETON_ID`. `verbose_name = verbose_name_plural = "Ustawienia AI"`.
- [x] backend-agent: w tym samym pliku `PostGenerator(AIProviderSettings)` — proxy model (`class Meta: proxy = True`), `verbose_name = verbose_name_plural = "Post z AI"`. Bez własnej tabeli w DB — dzieli tabelę z `AIProviderSettings`; służy wyłącznie do drugiej rejestracji w adminie pod innym `ModelAdmin` (patrz sekcja 4).
- [x] backend-agent: `uv run manage.py makemigrations ai_content` → `ai_content/migrations/0001_initial.py`, commitowana osobno od reszty kodu (`conventions.md`).

### 3. Pydantic schema i serwis generujący
- [x] backend-agent: `ai_content/schemas.py` — `GeneratedPostContent(pydantic.BaseModel)`: `title: str` (`max_length=200`), `excerpt: str` (`max_length=400`), `content: str` (bez limitu), `meta_title: str` (`max_length=60`), `meta_description: str` (`max_length=160`), `cover_image_alt: str` (`max_length=200`), `seo_rationale: str`. Limity 1:1 z polami `blog.models.PostTranslation`/`core.constants` — łapią przesadzone wyjście modelu już na warstwie Pydantic.
- [x] backend-agent: `ai_content/services.py` — `PostGenerationError(Exception)` (treść w `args[0]` to gotowy komunikat po polsku do `messages.error`).
- [x] backend-agent: w `services.py` — `_build_system_prompt(topic: str, local_focus: str) -> str`: rola (redaktor SEO blogu optometrycznego, pisze po polsku), temat, fokus lokalny, limity długości pól (te same liczby co w `schemas.GeneratedPostContent`) + przypomnienie, że treść i tak przejdzie sanityzację `blog.sanitization.sanitize_post_html` po stronie Django. **Odchylenie od planu:** allowlista tagów HTML w promptcie zbudowana z `core.sanitization.ALLOWED_TAGS`, nie z kluczy `blog.models.POST_CONTENT_EXTENSIONS` — klucze edytora WYSIWYG (`Typographic`, `History`, `HTML`...) opisują przyciski, nie tagi, więc mapowanie 1:1 byłoby dla części z nich niejednoznaczne; `ALLOWED_TAGS` to i tak egzekwowalna prawda przy zapisie, więc prompt ma się do niej dostosować.
- [x] backend-agent: w `services.py` — `generate_post_content(*, topic: str, local_focus: str, ai_settings: AIProviderSettings) -> GeneratedPostContent`: `init_chat_model(model=ai_settings.model_name, model_provider=ai_settings.provider, temperature=ai_settings.temperature, max_tokens=ai_settings.max_output_tokens, timeout=60).with_structured_output(GeneratedPostContent).invoke(_build_system_prompt(topic, local_focus))`. Całość w `try/except Exception` (brak klucza/timeout/błąd providera/nieudana walidacja Pydantic wszystkie lądują tu, LangChain nie gwarantuje jednego typu wyjątku) — log przez `logging.getLogger(__name__).exception(...)` (szczegóły **nigdy** do usera, `security.md`), `raise PostGenerationError("Nie udało się wygenerować treści posta. Sprawdź konfigurację dostawcy AI (klucz API w zmiennych środowiskowych, nazwa modelu) i spróbuj ponownie.") from exc`.
- [x] backend-agent: w `services.py` — `create_draft_post_from_generated_content(generated: GeneratedPostContent, *, author: "AbstractUser") -> Post`: w `transaction.atomic()` — `Post(author=author)` → `full_clean()` → `save()`, potem `PostTranslation(master=post, language_code=Language.PL, status=PostStatus.DRAFT, title=generated.title, excerpt=generated.excerpt, content=generated.content, meta_title=generated.meta_title, meta_description=generated.meta_description, cover_image_alt=generated.cover_image_alt)` → `full_clean()` → `save()` (slug dogeneruje się sam w `PostTranslation.save()`, `cover_image` zostaje puste — obrazek wgrywa człowiek, zgodnie z decyzją). `except django.core.exceptions.ValidationError as exc: raise PostGenerationError("Wygenerowana treść nie przeszła walidacji (np. za długi tytuł lub opis SEO). Żaden post nie został utworzony — zmień temat i spróbuj ponownie.") from exc` — `transaction.atomic()` gwarantuje, że `Post` nie zostaje w bazie osierocony bez tłumaczenia.

### 4. Formularz i panel admina
- [x] backend-agent: `ai_content/forms.py` — `PostGenerationForm(forms.Form)` (zwykły `Form`, nie `ModelForm` — nie ma modelu do wypełnienia): `topic = forms.CharField(label="Temat posta", max_length=200)`, `local_focus = forms.CharField(label="Fokus lokalny", max_length=200, initial="Wrocław, Polska")`. Komunikaty błędów po polsku wprost na polach (`error_messages=...`), styl jak `about.forms.AboutMeAdminForm`.
- [x] backend-agent: `ai_content/admin.py` — `AIProviderSettingsAdmin(admin.ModelAdmin)` rejestrowany na `AIProviderSettings`: `fields = ("provider", "model_name", "temperature", "max_output_tokens")`; `has_add_permission` i `changelist_view` skopiowane 1:1 z `about.admin.AboutMeAdmin` (redirect do edycji/dodania singletona, sprawdzenie `has_view_or_change_permission` **przed** przekierowaniem — ten sam powód: uniknięcie wycieku PK przez 302 dla staff bez uprawnień).
- [x] backend-agent: w `admin.py` — `PostGeneratorAdmin(admin.ModelAdmin)` rejestrowany na `PostGenerator`: `has_module_permission`/`has_view_permission` → `request.user.has_perm("blog.add_post")` (uprawnienie już istniejące na `Post`, bez nowych permission na `ai_content`); `has_add_permission`/`has_change_permission`/`has_delete_permission` → zawsze `False` (jedyna droga zapisu to `changelist_view` niżej, nie generyczny CRUD admina). `changelist_view` override: brak uprawnień → `return super().changelist_view(request, extra_context)` (ten sam wzorzec 403 co `AboutMeAdmin`); GET → renderuje pusty `PostGenerationForm()`; POST → `form = PostGenerationForm(request.POST)`, jeśli nieważny — renderuj ponownie z błędami; jeśli ważny — `AIProviderSettings.objects.first()`; `None` → `messages.error(request, "Najpierw skonfiguruj dostawcę AI w zakładce „Ustawienia AI”.")` + formularz ponownie; w przeciwnym razie `try: generated = generate_post_content(...); post = create_draft_post_from_generated_content(generated, author=request.user) except PostGenerationError as exc: messages.error(request, str(exc))` + formularz ponownie (wpisany `topic`/`local_focus` zostaje, bo formularz budowany z `request.POST`); sukces → `messages.success(request, format_html('Post „{}” utworzony jako szkic. <a href="{}">Edytuj</a>. Uzasadnienie SEO: {}', generated.title, reverse("admin:blog_post_change", args=[post.pk]), generated.seo_rationale))` + `HttpResponseRedirect` na ten sam URL.
- [x] backend-agent: `ai_content/templates/admin/ai_content/postgenerator/changelist.html` — rozszerza `admin/base_site.html`, prosty formularz (`{% csrf_token %}`, `{{ form.as_p }}`, przycisk submit w standardowej klasie `.submit-row`), bez własnego CSS — panel admina obsługuje osoba nietechniczna, ma wyglądać jak reszta Django Admin (`content-admin.md`).

### 5. Testy (qa-agent)
- [x] qa-agent: `ai_content/tests/__init__.py`, `ai_content/tests/conftest.py` — fixture `ai_provider_settings` (tworzy `AIProviderSettings` z sensownymi wartościami domyślnymi, np. `provider=AIProvider.ANTHROPIC, model_name="claude-test"`), fixture `mock_generated_content` (gotowy `GeneratedPostContent` do wstrzyknięcia w zamockowany serwis), fixtures uprawnień wzorem `about/tests/test_admin.py` (`django_user_model.objects.create_user(..., is_staff=True)` + `user_permissions.add(Permission.objects.get(content_type__app_label="blog", codename="add_post"))`).
- [x] qa-agent: `ai_content/tests/test_models.py` — `AIProviderSettings.save()` wymusza `pk=1` niezależnie od tego, co przyjdzie (analogicznie do testu singletona `about`); `PostGenerator` faktycznie współdzieli tabelę z `AIProviderSettings` (utworzony przez jeden model jest widoczny przez drugi, np. `PostGenerator.objects.filter(pk=ai_provider_settings.pk).exists()`).
- [x] qa-agent: `ai_content/tests/test_services.py` — `_build_system_prompt` zawiera temat i fokus lokalny w wygenerowanym tekście; `generate_post_content` z zamockowanym `init_chat_model` (monkeypatch na `ai_content.services.init_chat_model`) zwraca `GeneratedPostContent` przy sukcesie i podnosi `PostGenerationError` z polskim komunikatem, gdy zamockowany łańcuch rzuca wyjątek (wystarczy jeden generyczny wyjątek — obsługa jest jednym `except Exception`, reprezentuje zarówno brak klucza, jak i timeout czy błąd providera); `create_draft_post_from_generated_content` mapuje poprawnie pola na `Post`+`PostTranslation(status=PostStatus.DRAFT, language_code=Language.PL)`; przy sztucznie za długim polu (np. 500-znakowy `meta_title` wstrzyknięty bezpośrednio do `GeneratedPostContent` z pominięciem walidacji Pydantic, symulujący model, który zignorował instrukcję) podnosi `PostGenerationError` i **nie zostawia** żadnego `Post` w bazie (`Post.objects.count() == 0` po wyjątku — dowód działania `transaction.atomic()`).
- [x] qa-agent: `ai_content/tests/test_admin.py` — `AIProviderSettingsAdmin`: te same przypadki co `about/tests/test_admin.py` (dodanie zablokowane, gdy singleton istnieje; redirect z listy do edycji/dodania; 403 dla staff bez uprawnień, redirect zachowany dla uprawnionego). `PostGeneratorAdmin`: GET z `blog.add_post` → 200 z formularzem; GET bez uprawnienia → 403; POST z zamockowanym `generate_post_content` (sukces) → tworzy `Post`+`PostTranslation` w `pl`/`draft`, redirect na `admin:blog_post_change`, `messages` zawiera link i `seo_rationale`; POST bez skonfigurowanego `AIProviderSettings` → `messages.error`, `Post.objects.count() == 0`, formularz ponownie na stronie; POST z zamockowanym `generate_post_content` podnoszącym `PostGenerationError` → `messages.error(str(exc))`, `Post.objects.count() == 0`, wpisany temat nadal widoczny w formularzu.

### 5a. Rozszerzenie: edytowalne instrukcje dla AI (dodane po sekcji 5, 2026-09-20)
Poza pierwotnymi „Decyzjami wejściowymi” — padło w rozmowie po sekcji 5: zamiast hardkodować w kodzie personę/ton („pisz jak doświadczony optometrysta”) czy wytyczne SEO, redaktor ma dostać do tego edytowalne pole w panelu (ten sam wzorzec co `local_focus` w `PostGenerationForm` — edytowalne, z sensownym domyślnym tekstem, nigdy hardkodowane w kodzie). RAG (retrieval z istniejących postów) świadomie **nie** wchodzi w zakres — zanotowane w `docs/todo/TODO.md`, YAGNI.
- [x] backend-agent: `ai_content/models.py` — nowe pole na `AIProviderSettings`: `extra_instructions = models.TextField(verbose_name="Dodatkowe instrukcje dla AI", blank=True, default="Pisz jak doświadczony optometrysta — rzeczowo, z autorytetem. Stosuj sprawdzone zasady SEO: jasna struktura nagłówków, odpowiedź na intencję wyszukiwania, zasady E-E-A-T.", help_text="Doklejane do promptu przy każdym generowaniu — persona, ton, wytyczne SEO. Możesz zostawić puste albo zmienić na własne.")`. Migracja: `uv run manage.py makemigrations ai_content` (pole dodatkowe z `default=`, brak istniejących danych produkcyjnych do migrowania — branch jeszcze niezmergowany).
- [x] backend-agent: `ai_content/admin.py` — dopisać `"extra_instructions"` do `AIProviderSettingsAdmin.fields`, z widgetem `forms.Textarea` (podobnie jak `excerpt` w `blog.forms.PostAdminForm.Meta.widgets`).
- [x] backend-agent: `ai_content/services.py` — `_build_system_prompt(topic, local_focus, extra_instructions)`: jeśli `extra_instructions` niepuste, dopisz sekcję na końcu promptu, np. `"\n\nDodatkowe wytyczne od redakcji:\n{extra_instructions}"`. `generate_post_content` przekazuje `ai_settings.extra_instructions`.
- [x] backend-agent: zaktualizować `ai_content/tests/` (fixture `ai_provider_settings` w `conftest.py`, testy `_build_system_prompt` w `test_services.py`) pod nową sygnaturę/pole — to jedyny wyjątek od zasady „backend-agent nie dotyka katalogów testów”, bo zmiana sygnatury bezpośrednio wymaga zaktualizowania istniejących wywołań w testach, nie dopisania nowych przypadków (te dopisze `qa-agent` przy najbliższym review, jeśli uzna za potrzebne). W praktyce backend-agent dopisał też 2 małe testy nowej gałęzi (`test_prompt_zawiera_dodatkowe_instrukcje_gdy_niepuste`, `test_prompt_bez_sekcji_dodatkowych_instrukcji_gdy_puste`) — uznane za tanie i bezpośrednio powiązane, nie za rozszerzenie zakresu.
- [x] `/check` po zmianie — zielone (`ruff`/`mypy`/`manage.py check`/`makemigrations --dry-run` czyste, `pytest -q` — **243 passed**, zweryfikowane niezależnie).

### 6. Dokumentacja i domknięcie
- [ ] backend-agent: `docs/decisions/2026-09-20-generator-postow-ai.md` — nowy plik formalizujący architekturę (nowa aplikacja `ai_content`, singleton `AIProviderSettings`, `init_chat_model` + `with_structured_output`, klucze wyłącznie w zmiennych środowiskowych, proxy-model do UI w adminie, generacja tylko PL), wzorem `docs/decisions/2026-09-19-model-about-me.md` dla taska 9 — to, co dziś żyje tylko w sekcji „Decyzje wejściowe” wyżej.
- [ ] backend-agent: `CLAUDE.md` — przenieść „Sekrety bez AWS” z „Otwarte decyzje” do „Rozstrzygnięte”, z odnośnikiem do nowego pliku decyzji (rozstrzygnięte: zmienne środowiskowe czytane bezpośrednio przez biblioteki, bez Vault/AWS Secrets Manager).
- [ ] `/check` (ruff, mypy, `pytest`, `manage.py check`, `makemigrations --dry-run`) — zielone.
- [ ] qa-agent: niezależne review całości (regresje w `blog`, bezpieczeństwo kluczy/sanityzacji, brak wycieku draftów, zgodność z `.claude/rules/`).
- [ ] backend-agent: naprawa znalezisk z review qa-agent.
- [ ] `/code-review` (poziom medium) i naprawa znalezisk.
- [ ] Aktualizacja tego pliku — odhaczona checklista, `Status: gotowe`, wynik `/check`/review/`/code-review` udokumentowany w sekcji „Decyzje po drodze” (wzorem `docs/tasks/9-strona-o-mnie.md`).
- [ ] Merge do `dev` dopiero po zamknięciu review — osobna, świadoma decyzja użytkownika (`Workflow Git` w `CLAUDE.md`), nie automatyczny krok tego planu.

## Poza zakresem tego taska
Tłumaczenie EN generowane przez AI, kolejka/async (Celery), zewnętrzne narzędzie do sekretów (Vault/Infisical), kontekst z istniejących postów (linkowanie wewnętrzne, unikanie duplikatów tematów), limity/kwoty kosztowe poza `max_output_tokens`, generowanie dla `about` (tylko `blog` w tym tasku).

## Jak wznowić w nowej sesji

1. Nowa sesja Claude Code w tym repo, branch startowy `dev`, working tree czysty poza tym plikiem (patrz punkt 4 niżej).
2. Powiedz coś w stylu: „kontynuuj `docs/tasks/12-generator-postow-ai.md` — zrób plan implementacji”. Cały design jest w tym pliku, nie trzeba niczego przypominać ani ponownie tłumaczyć.
3. Zanim zacznie się kodowanie, oczekuj: (a) utworzenia brancha `12-generator-postow-ai` z `dev`, (b) wywołania skilla `writing-plans`, który rozpisze checklistę w sekcji „Plan” wyżej na konkretne kroki między agentami (`backend-agent` dla modeli/adminu/serwisu LangChain, `qa-agent` na testy i review).
4. **Ten plik nie jest jeszcze scommitowany** — leży tylko w working tree na `dev` (świadomie, `git commit` robi się dopiero na wniosek). Pierwszy commit na nowym branchu powinien go objąć, wzorem `docs(tasks): plan i historia decyzji taska 11` z taska 11.

## Decyzje po drodze

### Sekcje 1–2 zrealizowane (2026-09-20)
`backend-agent` dostarczył zależności LangChain (`langchain`, `langchain-anthropic`,
`langchain-openai`, `langchain-xai`, `uv add`), szkielet aplikacji `ai_content`
i model `AIProviderSettings` + proxy `PostGenerator`, w dwóch commitach:
`5a948e3` (zależności + szkielet + `env.example`), `03173d6` (model + migracja).
Zweryfikowane: `ruff check .` czyste, `mypy src` — 106 plików bez błędów,
`manage.py check` bez zastrzeżeń, `makemigrations --dry-run` po commitach —
brak zmian. Migracja `ai_content/migrations/0001_initial.py` potwierdzona
ręcznie: `CreateModel` dla `AIProviderSettings` (4 pola), osobny wpis dla
`PostGenerator` z `fields=[]` i `'proxy': True` — proxy nie tworzy nowej
tabeli, zgodnie z decyzją #7.

### Sekcja 3 zrealizowana (2026-09-20)
`backend-agent` dostarczył `ai_content/schemas.py` (`GeneratedPostContent`)
i `ai_content/services.py` (`PostGenerationError`, `_build_system_prompt`,
`generate_post_content`, `create_draft_post_from_generated_content`),
commit `fc3233d`. Allowlista tagów HTML w promptcie zbudowana z
`core.sanitization.ALLOWED_TAGS`, nie z kluczy `POST_CONTENT_EXTENSIONS`
(patrz uzasadnienie w checkliście sekcji 3 wyżej). `PostTranslation.full_clean()`
działa bez `exclude=["slug"]` — potwierdzone eksperymentalnie: `save()`
zawsze uzupełnia slug przed zapisem, więc pusty slug w momencie walidacji
nigdy nie koliduje z innym wierszem. Zweryfikowane: `ruff check .` czyste
(2 nowe pliki), `mypy src` — 108 plików bez błędów, ręczny smoke-test przez
`docker compose exec backend python manage.py shell` — `create_draft_post_from_generated_content`
tworzy `Post`+`PostTranslation(pl, draft)` bez wyjątku, dane testowe usunięte
po teście.

### Sekcja 4 zrealizowana (2026-09-20)
`backend-agent` dostarczył `ai_content/forms.py` (`PostGenerationForm`),
`ai_content/admin.py` (`AIProviderSettingsAdmin`, `PostGeneratorAdmin`) i
`ai_content/templates/admin/ai_content/postgenerator/changelist.html`,
commit `c9a132f`. `AIProviderSettingsAdmin` — kopia wzorca
`about.admin.AboutMeAdmin` (`has_add_permission` + `changelist_view` z
kontrolą uprawnień przed przekierowaniem). `PostGeneratorAdmin` blokuje
generyczny CRUD (`has_add/change/delete_permission` → `False`), dostęp
wymaga `blog.add_post`, a `changelist_view` obsługuje GET (pusty formularz)
i POST (walidacja → brak `AIProviderSettings` → `messages.error`; sukces →
`create_draft_post_from_generated_content` + redirect na
`admin:blog_post_change` z `messages.success` zawierającym link i
`seo_rationale`; `PostGenerationError` → `messages.error(str(exc))`, temat
zostaje w formularzu bo budowany z `request.POST`).

Rozstrzygnięcie własne: `request.user` w widoku admina jest typowany przez
django-stubs jako `AbstractBaseUser | AnonymousUser`, więc wywołanie
`create_draft_post_from_generated_content(..., author=request.user)`
(oczekuje `AbstractUser`) nie przechodziło `mypy`. Dodany
`assert isinstance(request.user, AbstractUser)` tuż przed wywołaniem, z
komentarzem że `has_view_or_change_permission` wyżej już gwarantuje
zalogowanego staff — nie zmienia zachowania w runtime, tylko domyka typy.

Zweryfikowane: `ruff check .` czyste, `mypy src` — 110 plików bez błędów
(uruchomione z `DEBUG=True SECRET_KEY=...` w env, bo `.env` nie istnieje w
tym środowisku — `manage.py check` tak samo, bez zastrzeżeń;
`makemigrations --check --dry-run` — „No changes detected" (baza lokalna
niedostępna spoza kontenera, ostrzeżenie nieistotne dla wyniku). Smoke-test
przez `docker compose exec backend python manage.py shell` z `django.test.Client`
(po `migrate ai_content` w kontenerze deweloperskim, który jeszcze nie miał
tej migracji zaaplikowanej): `/panel-redakcyjny/ai_content/aiprovidersettings/`
→ `302` na `.../add/` bez singletona; `/panel-redakcyjny/ai_content/postgenerator/`
→ `200` z formularzem (`id_topic` obecne) dla stafa z `blog.add_post`, `403`
bez tego uprawnienia (obie zakładki); POST bez skonfigurowanego
`AIProviderSettings` → `200`, komunikat „Najpierw skonfiguruj dostawcę AI…”
w treści, `0` nowych postów; POST z zamockowanym `ai_content.admin.generate_post_content`
(sukces) → `302` na `admin:blog_post_change`, nowy `Post`+`PostTranslation(pl, draft)`
ze slugiem wygenerowanym automatycznie; POST z zamockowanym wyjątkiem
`PostGenerationError` → `200`, komunikat błędu w treści, wpisany temat
zachowany w polu formularza, `0` nowych postów. Wszystkie dane testowe
usunięte po smoke-teście.

### Sekcja 5 zrealizowana + poprawka uprawnień (2026-09-20)
`qa-agent` dostarczył 21 nowych testów w `ai_content/tests/` (`test_models.py`,
`test_services.py`, `test_admin.py`), commit `2389f5d`. Cały pakiet: 240
passed, `ruff`/`mypy` czyste. Podczas pisania testów `qa-agent` zauważył (nie
zgłosił jako defekt, zostawił do oceny): `PostGeneratorAdmin` wymagał tylko
`blog.add_post`, a sukces generowania zawsze przekierowuje na
`admin:blog_post_change`, który wymaga `blog.change_post` — konto z samym
`add_post` trafiałoby na `403` zaraz po wygenerowaniu posta. Naprawione od
razu (nie odłożone do `docs/todo/`, bo to defekt w kodzie z tego samego
taska, nie osobny temat): `PostGeneratorAdmin._can_generate` wymaga teraz
`blog.add_post` **i** `blog.change_post`; fixture `staff_with_add_post_permission`
i test `test_get_z_samym_add_post_bez_change_post_zwraca_403` zaktualizowane
odpowiednio. Commit `03a692f`. Po poprawce: 241 passed (240 + 1 nowy test),
`ruff`/`mypy` nadal czyste.

### Sekcja 5a zrealizowana (2026-09-20)
`backend-agent` dostarczył pole `AIProviderSettings.extra_instructions`
(`TextField`, `blank=True`, z domyślnym tekstem „Pisz jak doświadczony
optometrysta…” + wytyczne SEO/E-E-A-T), migrację `0002_aiprovidersettings_
extra_instructions.py` (jeden `AddField`, addytywna), widget `Textarea` w
`AIProviderSettingsAdmin`, i doklejanie tekstu do promptu w
`_build_system_prompt` tylko gdy pole niepuste. Commit `a43e417`. Dwie
notatki poszły do `docs/todo/TODO.md` przy okazji tej rozmowy: RAG (osobny,
duży temat, świadomie poza zakresem) i wersjonowanie system promptów
(częściowo pokryte za darmo przez historię zmian w Django Admin —
`django.contrib.admin.models.LogEntry`; pełne powiązanie posta z dokładną
wersją promptu odłożone do rewizji, gdy funkcja zacznie być realnie
używana). Zweryfikowane niezależnie: `pytest -q` — **243 passed**.
