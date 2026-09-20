# Generator postów AI: aplikacja `ai_content`, singleton konfiguracji, proxy-model do UI

- **Decyzja:** Nowa aplikacja domenowa `ai_content` (nie wewnątrz `blog`), importująca `blog.models.Post`/`PostTranslation` do zapisu wyniku. Konfiguracja dostawcy LLM żyje w singletonie `AIProviderSettings` (`provider`, `model_name`, `temperature`, `max_output_tokens`, `extra_instructions`), edytowanym w zakładce „Ustawienia AI”. Generowanie posta odbywa się przez proxy-model `PostGenerator` (ta sama tabela co `AIProviderSettings`, bez własnej migracji), zarejestrowany pod osobnym `ModelAdmin` w zakładce „Post z AI”, który renderuje formularz (temat + fokus lokalny) zamiast generycznego CRUD-u admina. Wywołanie modelu idzie przez `init_chat_model(...).with_structured_output(GeneratedPostContent)` z LangChain — jedno, ujednolicone API niezależnie od tego, czy skonfigurowany dostawca to Anthropic, OpenAI czy xAI. Klucze API (`ANTHROPIC_API_KEY`/`OPENAI_API_KEY`/`XAI_API_KEY`) istnieją wyłącznie jako zmienne środowiskowe, czytane bezpośrednio przez LangChain — nigdy nie przechodzą przez kod, ustawienia ani logi Django. AI generuje tylko wersję PL, zawsze jako `PostTranslation(status=draft)`. `seo_rationale` (uzasadnienie wyboru SEO) trafia wyłącznie do komunikatu w adminie po sukcesie — nigdy do bazy. Dostęp do zakładki „Post z AI” wymaga jednocześnie `blog.add_post` **i** `blog.change_post`, bo udane generowanie zawsze przekierowuje na edycję nowo utworzonego posta.

- **Kontekst:** Redaktor bez wiedzy technicznej chce szybko dostać szkic posta (tytuł, treść, pola SEO) do dalszej edycji, zamiast pisać każdy wpis od zera. Szersze uzasadnienie „dlaczego LangChain” i „dlaczego to osobny task, nie część `7-dodanie-postu`” — `docs/decisions/2026-09-19-langchain-osobny-task.md`; ta decyzja rozwija tamtą o konkretną architekturę, nie zastępuje jej.

## Struktura

**`AIProviderSettings`** (singleton, `pk=1`, wzorem `about.models.AboutMe`)
- `provider` — `TextChoices` (`anthropic`/`openai`/`xai`), wartości identyczne ze stringami, jakich oczekuje `init_chat_model(model_provider=...)`
- `model_name` — `CharField` bez `choices`, wolny tekst
- `temperature`, `max_output_tokens` — parametry wywołania LLM, z walidatorami zakresu
- `extra_instructions` — `TextField`, `blank=True`, z domyślną personą/wytycznymi SEO, doklejany do promptu tylko gdy niepusty
- `save()` wymusza `pk=SINGLETON_ID`; admin (`has_add_permission`) blokuje drugi rekord

**`PostGenerator`** (proxy `AIProviderSettings`, `Meta.proxy = True`)
- bez własnej tabeli — druga „twarz” tego samego rekordu, wyłącznie do rejestracji w adminie pod innym `ModelAdmin`
- `has_add/change/delete_permission` zawsze `False` — jedyna droga zapisu to `changelist_view` renderujący `PostGenerationForm` i wołający `ai_content.services`

**`ai_content.schemas.GeneratedPostContent`** (Pydantic)
- `title`, `excerpt`, `content`, `meta_title`, `meta_description`, `cover_image_alt`, `seo_rationale`
- limity długości 1:1 z polami `blog.models.PostTranslation`/`core.constants`, żeby łapać przesadzone wyjście modelu już na warstwie Pydantic

**`ai_content.services`**
- `generate_post_content(...)` — wywołuje `init_chat_model(...).with_structured_output(GeneratedPostContent)`, jeden `try/except Exception` (LangChain nie gwarantuje jednego typu wyjątku na brak klucza, timeout, błąd providera czy nieudaną walidację Pydantic), szczegóły do logu, user dostaje jeden bezpieczny komunikat po polsku
- `create_draft_post_from_generated_content(...)` — w `transaction.atomic()` tworzy `Post` + `PostTranslation(language_code=Language.PL, status=PostStatus.DRAFT)`; `cover_image` zostaje puste, obrazek nadal wgrywa człowiek

## Uzasadnienia

- **Osobna aplikacja `ai_content`, nie kod w `blog`:** odwrócenie zależności (`engineering-principles.md`) — `blog` zostaje wolny od LangChain i trzech SDK providerów AI. `ai_content` importuje z `blog`, nigdy odwrotnie; gdyby generator AI kiedyś zniknął albo zmienił dostawcę, `blog` się tym nie przejmuje.
- **Proxy-model zamiast osobnego widoku spoza admina:** spójność z resztą panelu redakcyjnego (`content-admin.md`) — redaktor ma jeden, znajomy interfejs Django Admin, nie osobną stronę z innym wyglądem i innym systemem uprawnień. Ten sam trik co `AboutMeAdmin.changelist_view` (nadpisanie widoku listy), tylko renderujący formularz generowania zamiast przekierowania do edycji singletona.
- **`Post`/`PostTranslation` bez żadnych pól o AI:** czystość schematu — Pydantic i Django to dwie osobne warstwy (`docs/decisions/2026-09-19-langchain-osobny-task.md`). `seo_rationale` jest z natury efemeryczne (uzasadnienie decyzji generowania, nie treść posta) i istnieje tylko na czas jednego requesta/komunikatu; trzymanie go w bazie wymagałoby migracji `blog` pod potrzebę, która dotyczy wyłącznie `ai_content`.
- **`model_name` jako wolny tekst, bez `choices`:** dostawcy AI zmieniają i dodają nazwy modeli częściej, niż wychodzą nowe wersje tego panelu — sztywna lista wymuszałaby migrację/deploy przy każdej takiej zmianie, mimo że to nie jest zmiana schematu ani logiki.
- **`extra_instructions` jako edytowalne pole, nie zaszyta w kodzie persona:** redaktor decyduje o tonie i personie („pisz jak doświadczony optometrysta”), nic nie jest hardkodowane w kodzie Python. Świadoma decyzja z rozmowy przy tasku — nie zgadujemy tonu za redaktora, a zmiana wytycznych SEO/persony nie powinna wymagać zmiany kodu ani deploya.
- **Dostęp do „Post z AI” wymaga `blog.add_post` i `blog.change_post`:** sam `add_post` nie wystarcza, bo sukces zawsze przekierowuje na `admin:blog_post_change`, który wymaga `change_post`/`view_post`. Konto z samym `add_post` wygenerowałoby post i natychmiast dostałoby `403` na przekierowaniu — dostęp do zakładki ma sens tylko dla konta, które i tak może dokończyć pracę (przejrzeć i poprawić szkic).
- **Klucze API wyłącznie w zmiennych środowiskowych, czytane bezpośrednio przez LangChain:** zgodne z `security.md`/`scope.md` — bez AWS, bez nowego narzędzia do sekretów (Vault itp.). Klucz nigdy nie przechodzi przez kod, ustawienia ani logi Django, więc nie ma dodatkowej powierzchni wycieku poza samym środowiskiem procesu.

## Konsekwencje dla innych warstw

- Publiczne API i frontend nie wiedzą o istnieniu generatora — wynik to zwykły `Post`/`PostTranslation` w statusie `draft`, filtrowany tak samo jak każdy inny szkic (`security.md` — draft nigdy nie wycieka publicznym API).
- `env.example` dokumentuje `ANTHROPIC_API_KEY`/`OPENAI_API_KEY`/`XAI_API_KEY` jako zmienne czytane bezpośrednio przez LangChain, zakomentowane, bez wartości.
- Rozstrzyga otwartą pozycję „Sekrety bez AWS” z `CLAUDE.md` dla tego konkretnego przypadku (klucze dostawców AI) — zmienne środowiskowe czytane bezpośrednio przez bibliotekę, bez Vault/AWS Secrets Manager.

- **Status:** aktywna.
