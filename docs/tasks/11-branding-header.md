# 11 — Branding headera (logo + linki social media)

- **Cel:** Model `SiteBranding` (singleton: logo) + `SocialLink` (lista, FK do `SiteBranding`) w nowej aplikacji `branding`, panel redakcyjny w Django Admin, publiczne API `GET /api/v1/branding/`. Frontend (`Header.tsx`, `Footer.tsx`, favicon) pobiera logo i linki stamtąd zamiast statycznego `/logo.png`/`/icon.png` i zahardkodowanych `href="#"` — wygląd (rozmiar logo, rozmiar ikon) ma zostać identyczny z obecnym.
- **Status:** zmergowane do `dev`. Pozostaje tylko nota operacyjna (wgranie realnego logo + social linków w panelu, patrz plan niżej) — poza zakresem kodowym tego taska.

## Decyzje wejściowe

- Jeden model `SiteBranding` (singleton, wzorzec `about.AboutMe`: `save()` wymusza `pk=1`, admin blokuje drugi rekord, `changelist_view` przekierowuje wprost do edycji) z polem `logo` (`ImageField`, `core.validators.validate_image_upload` — ten sam wzorzec co `AboutMe.photo`/`Certificate.image`, więc nie otwiera na nowo nierozstrzygniętej decyzji o storage z `CLAUDE.md`).
- `SocialLink` — FK do `SiteBranding`, edytowany przez `TabularInline` (wzorzec `about.Certificate`/`CertificateInline`): `platform` (zamknięty wybór `SocialPlatform`: `linkedin`/`instagram`/`facebook` — te same trzy, co dziś we froncie, z tymi samymi ikonkami SVG), `url` (`URLField`), `order`. `UniqueConstraint(branding, platform)` — bez duplikatu tej samej platformy.
- Nowa platforma spoza tej trójki (np. TikTok) będzie wymagać jednorazowej pracy developera (nowa wartość enuma + ikonka SVG we froncie) — świadoma granica, nie luka: zamknięty wybór platformy jest wymogiem bezpieczeństwa (bez wklejania dowolnego SVG/HTML z panelu, `.claude/rules/security.md`).
- Jeden endpoint `GET /api/v1/branding/` (nie dwa) — front i tak pobiera logo i social linki razem do jednego headera. Zawsze `200`; przed pierwszą konfiguracją w panelu `{"logo": null, "social_links": []}`, nigdy `404`.
- Frontend: `getBranding()` w `lib/api/client.ts` (wzorzec `getAbout`, ISR `revalidate: 15s`), fetch w `layout.tsx` obok `getAboutSafely` z tym samym `try/catch`-degradacją. `logo` renderowany przez `toOptimizableImageSrc` (jak `AboutSection.tsx` dziś dla `about.photo`), z fallbackiem na statyczne `public/logo.png`, gdy `logo` jest `null` (świeży deploy / panel jeszcze pusty) — header nigdy nie ma zostać bez logo.
- Rozmiary (logo `width={80} height={80}`, wymiary/klasy ikon social w `Header.module.css`) zostają bez zmian — dane są teraz dynamiczne, markup/CSS wizualnie identyczny z obecnym stanem.

## Plan
- [x] backend-agent: aplikacja `branding` (domenowo, `scope.md`) — modele `SiteBranding` + `SocialLink` (+ `SocialPlatform` choices), migracje.
- [x] backend-agent: panel admina — `SiteBrandingAdmin` (singleton, wzorzec `AboutMeAdmin`) + `SocialLinkInline` (`TabularInline`, sortowanie `order`, dodawanie/usuwanie wierszy).
- [x] backend-agent: publiczny endpoint `GET /api/v1/branding/` — serializer, view (`core.api.CacheControlMixin`), throttling (osobny scope `branding`), `core.api.absolute_media_url` dla `logo`.
- [x] backend-agent: testy modelu (singleton, unikalność `platform`), adminu, serializera/widoku (pusty stan, pełny stan, throttling). 22 nowe testy, `pytest` całości: 199/199.
- [x] frontend-agent: `lib/api/types.ts` (`Branding`, `SocialLink`) + `lib/api/client.ts` (`getBranding`).
- [x] frontend-agent: `layout.tsx` — fetch (`Promise.all` obok `getAboutSafely`) + degradacja, przekazanie do `Header`.
- [x] frontend-agent: `Header.tsx` — logo z API (fallback `public/logo.png`), social linki z `.map()` po zarejestrowanych ikonach (`socialIcons.tsx`: platforma → SVG + aria-label z istniejącego słownika), bez zmiany wyglądu/rozmiarów. `.brandSocial` renderowany warunkowo (tylko gdy jest ≥1 pasujący link), żeby pusty/`null` branding nie zostawiał gapu w layoucie.
- [x] frontend-agent: `Header.test.tsx` zaktualizowany o `branding` prop (4 przypadki: pełne dane +/- `authorName`, `branding: null`, pusta `social_links`), snapshot zregenerowany i ręcznie przejrzany. `npm run lint`/`typecheck`/`test`: zielone (59/59 testów).
- [x] qa-agent: niezależne review — **GO** z 2 drobnymi zastrzeżeniami (braki w pokryciu testów, nieblokujące) + 1 obserwacją pre-istniejącego wzorca w `about`/`blog` (poza zakresem). Oba zastrzeżenia naprawione od razu (patrz "Naprawa znalezisk qa-agent" niżej).
- [x] `/check` zielone po ewentualnych naprawach (backend 200/200, frontend 60/60 — także po przeniesieniu assetów, patrz niżej).
- [~] `/code-review` — w toku: 3 znaleziska z jednego wątku (cross-file tracer), 2 naprawione od razu, 1 świadomie odłożone (patrz "Naprawa znalezisk /code-review" niżej). Czeka na potwierdzenie, czy to była całość reviewu.
- [ ] Po merge: ktoś wchodzi w panel i wgrywa obecne logo + uzupełnia social linki (baza startuje pusta) — nota operacyjna, nie krok kodowy.

- [x] frontend-agent: `Footer.tsx` pobiera logo z tego samego `branding` co `Header` (ten sam fetch w `layout.tsx`, bez dodatkowego zapytania), fallback `public/brand/logo.png` bez zmian.
- [x] frontend-agent: `app/icon.tsx` — dynamiczny favicon (Next.js 16, route function zamiast statycznego pliku), fetchuje `branding.logo`, przepisuje URL przez `toOptimizableImageSrc` (inaczej `ECONNREFUSED` server-side w Dockerze), `Content-Type` czytany z realnej odpowiedzi backendu (nie zahardkodowany — zweryfikowane `curl`, zgodny z realnym JPEG-iem z devowego uploadu), fallback statyczny plik przy braku logo. Stary `app/icon.png` usunięty.
- [x] backend-agent: poprawki z `/code-review` — `SiteBrandingSerializer.get_social_links` guard na `pk is None`, `SiteBrandingView` zawsze przez serializer (bez ręcznego literalu pustego stanu); `core.storage.RandomFilenameUploadTo` (`@deconstructible` — domknięcie funkcyjne nie serializuje się w migracjach Django, stąd klasa) używana tylko w `branding`, `blog`/`about` świadomie nietknięte (dotyczyłoby zaaplikowanych migracji poza zakresem brancha).
- [x] Naprawa: zdjęcia z telefonu (EXIF `Orientation`) wyglądały obrócone w faviconie (`app/icon.tsx` przepuszcza surowe bajty — renderowanie favikony w karcie przeglądarki często ignoruje EXIF, w odróżnieniu od `<img>` na stronie). `core.image_processing.normalize_image_orientation` (Pillow `ImageOps.exif_transpose`) wpięte w `SiteBranding.save()` — obraca piksele i usuwa flagę przy KAŻDYM świeżo wgranym logo (`isinstance(self.logo.file, UploadedFile)` odróżnia nowy upload od zwykłego re-save już zapisanego pliku, żeby nie przekodowywać/nie zmieniać nazwy pliku bez powodu). `about.photo`/`Certificate.image`/`blog.cover_image` mają ten sam potencjalny defekt, świadomie nieruszone w tym tasku (ten sam wzorzec co z `upload_to` — kandydat do osobnego zlecenia). Kwadratowy/prostokątny kształt favikony pozostaje bez zmian — to oczekiwane zachowanie (brak możliwości CSS-owego zaokrąglenia favikony), potwierdzone z użytkownikiem. 211/211 testów.
- [x] Kolejna runda `qa-agent` + `/code-review` po tych rozszerzeniach (stopka, favicon, refaktor serializera, normalizacja EXIF) — **NO-GO → naprawione**, patrz "Druga runda review" niżej.
- [x] `/check` zielone po tej rundzie (zakres celowany na zmienione pliki — backend w całości, frontend bez ponownego przebiegu, bo nic w nim nie zmieniła ta runda naprawy).
- [x] Merge do `dev` (4 atomowe commity na branchu: reguły procesowe, backend, frontend, docs — `git merge --no-ff`, bez konfliktów).

### Druga runda review (qa-agent + /code-review) — znaleziska i naprawy

**qa-agent** (werdykt: NO-GO, 4 blokujące + 1 drobne):
1. **Naprawione** — migracja `branding/migrations/0001_initial.py` zserializowana ze starej wersji `upload_to` (referencja do `branding.models.branding_logo_upload_to`, funkcji, która już nie istnieje — kod przeszedł na klasę `core.storage.RandomFilenameUploadTo`). Zamaskowane przez `makemigrations --check` (Django przy wczytywaniu migracji robi żywy import modułu). Migracja niewdrożona (branch niezmergowany) — zregenerowana, teraz referuje `core.storage.RandomFilenameUploadTo('branding/logo')`.
2. **Naprawione** — `app/icon.tsx`: `getBranding().catch(() => null)` połykał wyjątek bez logu.
3. **Naprawione** — `app/icon.tsx`: drugi `fetch()` (bajty loga) bez obsługi błędu sieciowego — rzucał 500 zamiast spadać do fallbacku. Oba naprawione razem: cała logika w jednym `try/catch`, log `console.error`, jedyny fallback poza `try` osiągalny z każdej ścieżki błędu.
4. **Naprawione** — zerowe pokrycie testami `app/icon.tsx` — dodany `icon.test.tsx` (5 przypadków: sukces, `logo: null`, wyjątek `getBranding()`, `!response.ok`, wyjątek drugiego fetcha).
5. **Naprawione** — JSDoc `toOptimizableImageSrc` (`lib/media/image-src.ts`) aktualizowany — nieprawdziwe już zawężenie "wyłącznie dla `<Image src>`".

**`/code-review`** (8 znalezisk, zweryfikowane osobno przed naprawą):
1. **Naprawione** — `SiteBranding.save()` odczytywał `self.logo.file` (property) nawet gdy logo nie było dotknięte (np. zapis tylko `SocialLink` w inline) — to wymuszało `storage.open()` na każdym takim zapisie, z ryzykiem `FileNotFoundError`, jeśli plik zniknął ze storage. Naprawa: warunek na `self.logo._committed` (ten sam atrybut, którego Django używa wewnętrznie w `FileField.pre_save()`) zamiast bezpośredniego dotknięcia `.file`. Test regresji: usunięcie pliku ze storage + `.save()` na świeżo wczytanej instancji nie rzuca wyjątku.
2. **Naprawione (częściowo, świadomie)** — `normalize_image_orientation` mogła wysypać się surowym wyjątkiem Pillow, jeśli plik przeszedł `Image.open().verify()` (nie robi pełnego decode), ale zawiódł przy realnym decode/re-encode. Zamienione na `ValidationError` z czytelnym komunikatem PL. **Świadomie odłożone**: to nie daje ładnego komunikatu w formularzu admina — zweryfikowałem w źródle Django, że `ModelAdmin._changeform_view`/`save_model` nie łapie `ValidationError` z `obj.save()`, więc `.save()`-time wyjątek i tak ląduje jako ogólny 500. Pełne rozwiązanie (miły komunikat inline) wymagałoby przeniesienia normalizacji do `Model.clean()`, co zmienia semantykę zapisów poza adminem (shell/fixture) i wymaga przepisania obu istniejących testów EXIF na `full_clean()` — uznane za nieproporcjonalne do rzadkości tego edge case'a (plik przechodzący `.verify()`, ale nie pełny decode, jest rzadki). Kandydat na osobne zlecenie, jeśli kiedyś rozszerzymy `normalize_image_orientation` na `about`/`blog`.
3. **Fałszywe/nieaktualne** — wskazywało, że EXIF nie jest naprawione dla `about.photo`. To nie nowe znalezisko — dokładnie ta sama, już opisana wyżej (punkt 32) świadomie odłożona decyzja.
4. **Bez akcji** — "duplikat" fetcha brandingu w `icon.tsx` vs `layout.tsx`: to nie defekt, to nieodłączna cecha dynamicznego faviconu (przeglądarka żąda `/icon` jako osobny request HTTP, niezależny od RSC renderu strony) — zamortyzowane przez istniejący `revalidate: 15s`. Budowanie dodatkowej warstwy cache pod ten scenariusz byłoby premature optimization.
5. **Fałszywe zgłoszenie** — `alt=""` na logo w `Header.tsx`. Zweryfikowane w diffie: linia istniała przed tym branchem (zmienił się tylko `src`), i to prawidłowy wzorzec accessibility — obraz jest w `<Link>` z `aria-label`, `alt=""` unika zdublowanego odczytu przez czytnik ekranu.
6. **Fałszywe zgłoszenie** — analogicznie w `Footer.tsx`, obok loga jest widoczny tekst „okowFormie" w tym samym `<p>`.
7. **Naprawione** — `branding/icons.py::social_platform_icon_html` nie miało żadnego bezpośredniego testu (gałąź nieznanej platformy — `mark_safe("")` — całkowicie nietestowana). Dodany `branding/tests/test_icons.py` (znana platforma → `<svg`, nieznana → pusty string bez wyjątku).
8. **Naprawione** — jakość zapisu JPEG (`quality=90`) była warunkowana na `image.format == "JPEG"` dosłownie — telefony z podwójną kamerą eksportujące `.jpg` jako kontener Pillow `"MPO"` dostawały domyślną (niższą) jakość Pillow. Naprawa: format zapisu wyliczany z już zwalidowanego rozszerzenia pliku (`_FORMAT_BY_EXTENSION`), nie z introspekcji Pillow.

Weryfikacja po naprawach 1/2/7/8 (backend, jedyny dotknięty zakres w tej turze): `pytest` 216/216, `ruff check` czyste, `mypy src` czyste (jeden uzasadniony `type: ignore[attr-defined]` na `_committed`), `makemigrations --check` bez zmian. Frontend celowo nie przebiegnięty ponownie w tej turze (nic w nim się nie zmieniło od ostatniego zielonego `/check`).

## Poza zakresem tego taska
Nowe platformy social media spoza `linkedin`/`instagram`/`facebook` (np. TikTok) — wymaga osobnego zlecenia (nowa ikonka + wartość enuma). Integracja z Instagramem w głębszym sensie (embed postów) — otwarta decyzja w `CLAUDE.md`, nie ten task.

## Decyzje po drodze

### Widok API jako `APIView`, nie `RetrieveAPIView`
`SiteBrandingView` używa zwykłego `rest_framework.views.APIView`, nie `generics.RetrieveAPIView` (w przeciwieństwie do `AboutDetailView`). `RetrieveAPIView.get_object()` z fallbackiem na nieutrwaloną instancję `SiteBranding()` miałby problem z dostępem do `social_links` (reverse FK manager na instancji bez `pk`) — jawne rozgałęzienie `None → {"logo": None, "social_links": []}` w `views.py` jest prostsze i bezpieczniejsze. Kontrakt (kształt JSON, zawsze `200`) bez zmian względem planu.

### Naprawa znalezisk qa-agent
- Frontend: dopisany test na nieznaną platformę z API (np. `tiktok`) — `socialIconRegistry[link.platform] !== undefined` filtruje ją poprawnie, reszta headera renderuje się bez wyjątku. 60/60 testów.
- Backend: dopisany test POST z zaznaczonym `DELETE` na formsetcie `SocialLinkInline` — wiersz faktycznie znika z bazy (nie tylko z widoku), drugi zostaje nietknięty. 200/200 testów.
- Trzecie znalezisko (niespójny język domyślnego komunikatu błędu Django przy duplikacie `UniqueConstraint`) — pre-istniejący wzorzec, obecny też w `about.models.AboutMeTranslation`; świadomie zostawiony poza zakresem tego taska, do ewentualnego osobnego zlecenia obejmującego obie apki.

### Podgląd ikonki platformy w Django Admin
Na prośbę użytkownika `SocialLinkInline` pokazuje teraz ikonkę SVG platformy (pierwsza kolumna, przed `platform`) — ta sama treść SVG co frontend (`branding/icons.py`, zweryfikowane programowo jako bit-identyczne z `Header/icons/*.tsx`), bo `.tsx` nie da się zaimportować do Pythona — świadome zdublowanie treści SVG między dwoma runtime'ami, nie defekt DRY. Kolor stały (`#333333`, bez hover-theming — w adminie niepotrzebne). Test: `<svg` faktycznie w odpowiedzi formularza edycji. 24/24 testów `branding`.

### Naprawa znalezisk /code-review (wątek "cross-file tracer")
1. **Naprawione** — `getBranding()` w `lib/api/client.ts` miał martwą gałąź `null` (dziedziczoną z generycznego `fetchApi<T>`, gdzie `null` = 404; `/api/v1/branding/` nigdy nie daje 404). Zawężone do `Promise<Branding>` — rzuca zamiast zwracać `null`, złapane przez istniejący `try/catch` w `getBrandingSafely()` (`layout.tsx`). `fetchApi`/`getAbout`/`getPosts`/`getPost` bez zmian.
2. **Naprawione** — JSDoc przy `HeaderProps.branding` doprecyzowany: `null` oznacza wyłącznie błąd pobrania, nie „panel nieskonfigurowany" (ten stan to zawsze `{logo: null, social_links: []}`, nigdy `null` na poziomie propa) — rozwiązane przez naprawę #1, bez osobnej zmiany logiki.
3. **Świadomie odłożone** — `SiteBranding` (singleton) wymuszony tylko w `save()`/adminie, bez ograniczenia na poziomie bazy. Dokładnie ten sam, już istniejący wzorzec co `about.AboutMe` — nie regresja tego brancha. Naprawa objęłaby też `about`, czyli zmianę schematu poza zakresem tego taska (`.claude/rules/engineering-principles.md`: zmiana schematu bazy wymaga zgody) — kandydat na osobne zlecenie obejmujące oba singletony naraz, żeby nie zostawić ich niespójnymi.

**Obserwacja poboczna (nie blokuje)**: `frontend/src/lib/api` nie ma dziś żadnej infrastruktury testowej (brak mocka `fetch` w całym `frontend/src`) — dodanie testu na nowe zachowanie `getBranding()` wymagałoby ustalenia wzorca (Vitest `vi.stubGlobal`/MSW), więc świadomie pominięte w tej poprawce zamiast zgadywania. Do rozważenia przy kolejnym tasku dotykającym `lib/api`.

### Porządkowanie statycznych assetów po review
Na prośbę użytkownika logo i ikonki social zostały przeniesione z płaskiej struktury do dedykowanych folderów:
- `public/logo.png` → `public/brand/logo.png` (fallback logo, statyczny plik) — zaktualizowano referencje w `Header.tsx` **i** `Footer.tsx` (Footer korzystał z tego samego pliku, złapane przy okazji, nie było wprost w zleceniu).
- Ikonki social (`Header/socialIcons.tsx`) → `Header/icons/` (`LinkedInIcon.tsx`/`InstagramIcon.tsx`/`FacebookIcon.tsx` + `index.tsx` z rejestrem). Świadomie zostały komponentami React z inline SVG, **nie** plikami `.svg` ładowanymi jako obrazek — `Header.module.css:58-68` zmienia kolor ikonki na hover przez CSS `color`/`currentColor`, co działa tylko dla SVG w tym samym DOM-ie; zewnętrzny plik `.svg` w `<img>`/`next/image` by tego nie odziedziczył i hover-kolor by się urwał.
- Testy i snapshoty (`Header`, `Footer`) zregenerowane i ręcznie przejrzane — jedyna zmiana treści to ścieżka `/logo.png` → `/brand/logo.png`. 60/60 testów, lint/typecheck czyste.

### Pusty `.brandSocial` nie jest renderowany wcale
`.brandLogoCol` w CSS ma `gap: 0.6rem` między dziećmi — renderowanie pustego `<div className={styles.brandSocial} />` zostawiłoby martwy odstęp pod logo, gdy brak linków (świeży deploy / błąd fetch). Zamiast warunku na zawartość `<div>`, cały blok jest pomijany w JSX, gdy `social_links` (po odfiltrowaniu nieznanych platform) jest puste — layout identyczny z headerem bez sekcji social w ogóle. Potwierdzone w snapshotach: `branding: null` i pusta `social_links` kończą markup od razu po `</a>` z logo.
