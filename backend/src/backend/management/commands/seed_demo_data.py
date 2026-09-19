"""Wypełnij pustą bazę realistycznymi danymi demo.

Po co: `/backend` ma gotowe, opublikowane, read-only API (`/api/v1/{lang}/about/`,
`/api/v1/{lang}/posts/`), ale świeża baza jest pusta — publiczne endpointy
zwracałyby puste listy/404. Frontend Next.js (kolejny krok tego samego taska,
`docs/tasks/10-live-frontend-nextjs.md`) potrzebuje realnej treści, żeby dało
się zbudować i zweryfikować strony bez czekania na ręczne wypełnienie panelu
redakcyjnego. Stąd jedna komenda kompozycyjna zamiast fixtures Django: fixtures
serializowałyby też obrazy jako base64 w JSON, a tu obrazy trzeba wygenerować
programistycznie (`.claude/rules/security.md` — zero plików binarnych w repo).

Umieszczona na poziomie projektu (`backend/src/backend/`), nie w `about` ani w
`blog`: obie domeny celowo się nie importują nawzajem
(`.claude/rules/scope.md`), a ta komenda seeduje dane w obu naraz.

Idempotentna: `get_or_create` na każdym poziomie (konto, singleton „O mnie",
tłumaczenia, certyfikaty, posty) — bezpieczne wielokrotne uruchomienie bez
duplikatów i bez ponownego generowania (a więc mnożenia) obrazów.
"""

import textwrap
from datetime import timedelta
from io import BytesIO
from typing import Any, Final, NotRequired, TypedDict

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.utils import timezone
from PIL import Image, ImageDraw, ImageFont

from about.models import AboutMe, AboutMeTranslation, Certificate
from accounts.models import User
from blog.constants import Language, PostStatus
from blog.models import Post, PostTranslation
from core.constants import PublicationStatus as AboutStatus

DEMO_AUTHOR_USERNAME: Final[str] = "demo-author"
DEMO_AUTHOR_EMAIL: Final[str] = "demo-author@okowformie.pl"
DEMO_AUTHOR_FIRST_NAME: Final[str] = "Anna"
DEMO_AUTHOR_LAST_NAME: Final[str] = "Kowalska"

ABOUT_FULL_NAME: Final[str] = f"{DEMO_AUTHOR_FIRST_NAME} {DEMO_AUTHOR_LAST_NAME}"
ABOUT_PHOTO_COLOR: Final[tuple[int, int, int]] = (78, 121, 118)
POST_COVER_COLOR: Final[tuple[int, int, int]] = (58, 92, 120)
CERTIFICATE_COLORS: Final[tuple[tuple[int, int, int], ...]] = (
    (120, 78, 90),
    (90, 110, 78),
    (78, 98, 120),
    (120, 104, 78),
    (100, 78, 120),
    (78, 120, 112),
    (120, 90, 78),
    (94, 78, 120),
)


class AboutTranslationSeed(TypedDict):
    headline: str
    bio: str
    photo_alt: str
    meta_title: str
    meta_description: str


ABOUT_TRANSLATIONS: Final[dict[str, AboutTranslationSeed]] = {
    Language.PL: {
        "headline": "Optometrystka i pasjonatka zdrowego widzenia",
        "bio": (
            "<p>Nazywam się Anna Kowalska i od ponad dziesięciu lat zajmuję się "
            "optometrią — doborem soczewek kontaktowych, okularów oraz diagnostyką "
            "wad wzroku u dzieci i dorosłych.</p>"
            "<p>Prowadzę ten blog, żeby dzielić się wiedzą, która realnie pomaga: "
            "jak bezpiecznie nosić soczewki kontaktowe, kiedy warto zabrać dziecko "
            "na pierwszą wizytę ortoptyczną i jak wygląda adaptacja do okularów "
            "progresywnych.</p>"
            "<h2>Doświadczenie</h2>"
            "<ul>"
            "<li>Ponad 3000 przeprowadzonych badań wzroku</li>"
            "<li>Specjalizacja w doborze soczewek kontaktowych dla początkujących</li>"
            "<li>Współpraca z gabinetami ortoptycznymi dla dzieci</li>"
            "</ul>"
            "<p>Prywatnie uwielbiam górskie wędrówki i dobrą kawę — a każdą wolną "
            "chwilę poświęcam na czytanie najnowszych badań z zakresu optometrii "
            "klinicznej.</p>"
        ),
        "photo_alt": "Anna Kowalska, optometrystka, uśmiechnięta w gabinecie optycznym",
        "meta_title": "Anna Kowalska — optometrystka | okowFormie",
        "meta_description": (
            "Anna Kowalska, optometrystka z ponad dziesięcioletnim doświadczeniem — "
            "dzieli się wiedzą o soczewkach kontaktowych, okularach i zdrowiu wzroku "
            "dzieci."
        ),
    },
    Language.EN: {
        "headline": "Optometrist and advocate for healthy vision",
        "bio": (
            "<p>My name is Anna Kowalska and for over ten years I have worked in "
            "optometry — fitting contact lenses and glasses, and diagnosing vision "
            "problems in children and adults.</p>"
            "<p>I run this blog to share knowledge that genuinely helps: how to wear "
            "contact lenses safely, when to take your child for a first orthoptic "
            "visit, and what adapting to progressive lenses actually feels like.</p>"
            "<h2>Experience</h2>"
            "<ul>"
            "<li>Over 3,000 eye examinations performed</li>"
            "<li>Specialising in fitting contact lenses for first-time wearers</li>"
            "<li>Working closely with orthoptic practices for children</li>"
            "</ul>"
            "<p>Outside the practice I love mountain hiking and good coffee — and I "
            "spend most of my free time reading the latest clinical optometry "
            "research.</p>"
        ),
        "photo_alt": "Anna Kowalska, optometrist, smiling in her optical practice",
        "meta_title": "Anna Kowalska — Optometrist | okowFormie",
        "meta_description": (
            "Anna Kowalska is an optometrist with over ten years of experience, "
            "sharing practical knowledge about contact lenses, glasses, and eye "
            "health for families."
        ),
    },
}


class CertificateSeed(TypedDict):
    name: str
    issuer: str
    issued_year: int


CERTIFICATES: Final[tuple[CertificateSeed, ...]] = (
    {"name": "Terapia widzenia I", "issuer": "Krakowska Szkoła Optometrii", "issued_year": 2018},
    {
        "name": "Ortoptyka — kurs bazowy",
        "issuer": "Warszawski Instytut Optyki Okulistycznej",
        "issued_year": 2019,
    },
    {
        "name": "Certyfikat optometrii",
        "issuer": "Polska Akademia Kontaktologii",
        "issued_year": 2020,
    },
    {"name": "Szkolenie kliniczne", "issuer": "Ośrodek Szkoleniowy VisusMed", "issued_year": 2021},
    {
        "name": "Warsztaty diagnostyczne",
        "issuer": "Centrum Diagnostyki Okulistycznej OptiCare",
        "issued_year": 2022,
    },
    {
        "name": "Diagnostyka jaskry",
        "issuer": "Instytut Diagnostyki Jaskry",
        "issued_year": 2023,
    },
    {
        "name": "Pierwsza pomoc okulistyczna",
        "issuer": "Szkoła Pierwszej Pomocy MedSafe",
        "issued_year": 2024,
    },
    {
        "name": "Fitting soczewek twardych",
        "issuer": "Europejskie Centrum Fittingu Soczewek Twardych",
        "issued_year": 2025,
    },
)


class PostTranslationSeed(TypedDict):
    slug: str
    title: str
    excerpt: str
    content: str
    cover_image_alt: str
    meta_title: str
    meta_description: str
    published_days_ago: int


class PostSeed(TypedDict):
    pl: PostTranslationSeed
    en: NotRequired[PostTranslationSeed]


POSTS: Final[tuple[PostSeed, ...]] = (
    {
        "pl": {
            "slug": "soczewki-kontaktowe-na-start",
            "title": "Soczewki kontaktowe na start — o czym warto wiedzieć",
            "excerpt": (
                "Zastanawiasz się nad pierwszymi soczewkami kontaktowymi? Wyjaśniamy, "
                "jak wygląda dobór soczewek, na co zwrócić uwagę przy pierwszym "
                "zakładaniu i jak dbać o higienę noszenia na co dzień."
            ),
            "content": (
                "<p><strong>Pierwsze soczewki kontaktowe</strong> to spora zmiana w "
                "codziennej pielęgnacji oczu — ale przy odrobinie przygotowania "
                "adaptacja przebiega szybko i bezproblemowo.</p>"
                "<h2>Jak wygląda dobór soczewek</h2>"
                "<p>Każdy dobór zaczyna się od badania wzroku i pomiaru krzywizny "
                "rogówki. Dopiero na tej podstawie optometrysta proponuje konkretny "
                "typ i moc soczewek — jednodniowe, miesięczne czy soczewki toryczne "
                "przy astygmatyzmie.</p>"
                "<h2>Higiena noszenia — podstawowe zasady</h2>"
                "<ul>"
                "<li>Zawsze myj ręce przed dotknięciem soczewki.</li>"
                "<li>Nie śpij w soczewkach, które nie są do tego przeznaczone.</li>"
                "<li>Wymieniaj soczewki zgodnie z zaleceniem — nie „na wyczucie”.</li>"
                "<li>Nigdy nie płucz soczewek wodą z kranu.</li>"
                "</ul>"
                "<h2>Najczęstsze błędy początkujących</h2>"
                "<p>Najczęstszym błędem jest zbyt długie noszenie soczewek w "
                "pierwszych dniach oraz ignorowanie uczucia suchości oka. Jeśli "
                "soczewka przeszkadza dłużej niż kilka minut, zdejmij ją i "
                "skonsultuj się z optometrystą.</p>"
                "<blockquote>Adaptacja do soczewek kontaktowych trwa zwykle od "
                "kilku dni do dwóch tygodni.</blockquote>"
            ),
            "cover_image_alt": "Dłoń trzymająca soczewkę kontaktową nad opakowaniem",
            "meta_title": "Soczewki kontaktowe na start | okowFormie",
            "meta_description": (
                "Pierwsze soczewki kontaktowe? Sprawdź, jak bezpiecznie zacząć: dobór "
                "soczewek, higiena noszenia i najczęstsze błędy początkujących "
                "opisane krok po kroku."
            ),
            "published_days_ago": 21,
        },
        "en": {
            "slug": "contact-lenses-for-beginners",
            "title": "Contact Lenses for Beginners — What You Should Know",
            "excerpt": (
                "Thinking about your first contact lenses? We explain how fitting "
                "works, what to watch for when inserting them for the first time, "
                "and how to keep your daily wear routine safe."
            ),
            "content": (
                "<p><strong>Your first pair of contact lenses</strong> is a real "
                "change in your daily eye care routine — but with a little "
                "preparation, adapting to them is quick and painless.</p>"
                "<h2>How lens fitting works</h2>"
                "<p>Every fitting starts with an eye exam and a measurement of your "
                "cornea's curvature. Only then does the optometrist suggest the "
                "right type and power — daily, monthly, or toric lenses for "
                "astigmatism.</p>"
                "<h2>Wear hygiene — the basics</h2>"
                "<ul>"
                "<li>Always wash your hands before touching a lens.</li>"
                "<li>Never sleep in lenses that are not designed for it.</li>"
                "<li>Replace lenses on schedule — not by how they feel.</li>"
                "<li>Never rinse lenses with tap water.</li>"
                "</ul>"
                "<h2>Common beginner mistakes</h2>"
                "<p>The most common mistake is wearing lenses too long in the first "
                "days and ignoring dryness. If a lens bothers you for more than a "
                "few minutes, remove it and consult your optometrist.</p>"
                "<blockquote>Adapting to contact lenses usually takes a few days to "
                "two weeks.</blockquote>"
            ),
            "cover_image_alt": "A hand holding a contact lens above its blister pack",
            "meta_title": "Contact Lenses for Beginners | okowFormie",
            "meta_description": (
                "Considering your first contact lenses? Learn how to start safely: "
                "fitting, hygiene, and the most common beginner mistakes explained "
                "by an optometrist."
            ),
            "published_days_ago": 20,
        },
    },
    {
        "pl": {
            "slug": "ortoptyka-u-dzieci-kiedy-sie-zglosic",
            "title": "Ortoptyka u dzieci — kiedy warto się zgłosić",
            "excerpt": (
                "Zezowanie, częste mrużenie oczu czy potykanie się o przedmioty mogą "
                "być sygnałem, że dziecko potrzebuje wizyty ortoptycznej. "
                "Podpowiadamy, na co zwrócić uwagę i kiedy się zgłosić."
            ),
            "content": (
                "<p><strong>Ortoptyka</strong> zajmuje się diagnozowaniem i "
                "leczeniem zaburzeń widzenia obuocznego u dzieci — między innymi "
                "zeza i niedowidzenia.</p>"
                "<h2>Sygnały, które powinny zaniepokoić rodzica</h2>"
                "<ul>"
                "<li>Widoczne zezowanie, nawet sporadyczne</li>"
                "<li>Częste mrużenie lub przekrzywianie głowy podczas patrzenia</li>"
                "<li>Potykanie się o przedmioty, problem z oceną odległości</li>"
                "<li>Trzymanie książki bardzo blisko oczu</li>"
                "</ul>"
                "<h2>Jak wygląda pierwsza wizyta</h2>"
                "<p>Wizyta ortoptyczna jest bezbolesna i dostosowana do wieku "
                "dziecka. Obejmuje ocenę ruchomości oczu, badanie ostrości wzroku "
                "oraz testy widzenia obuocznego.</p>"
                "<h2>Kiedy się zgłosić</h2>"
                "<p>Zalecany wiek pierwszego badania to 3–4 lata, ale każdy "
                "niepokojący sygnał wcześniej jest wystarczającym powodem, żeby "
                "umówić wizytę bez czekania na wiek „standardowy”.</p>"
            ),
            "cover_image_alt": "Dziecko podczas badania wzroku u ortoptysty",
            "meta_title": "Ortoptyka u dzieci — kiedy się zgłosić | okowFormie",
            "meta_description": (
                "Zezowanie, częste mrużenie oczu, potykanie się o przedmioty — kiedy "
                "te sygnały u dziecka wymagają wizyty ortoptycznej? Praktyczny "
                "przewodnik dla rodziców."
            ),
            "published_days_ago": 14,
        },
    },
    {
        "pl": {
            "slug": "okulary-progresywne-adaptacja",
            "title": "Okulary progresywne — jak przebiega adaptacja",
            "excerpt": (
                "Pierwsze dni w okularach progresywnych bywają wymagające. "
                "Tłumaczymy, ile trwa adaptacja, jakie objawy są normalne, a które "
                "powinny skłonić do kontaktu z optometrystą."
            ),
            "content": (
                "<p>Okulary <strong>progresywne</strong> łączą kilka mocy w jednej "
                "soczewce — do dali, do bliży i strefy pośredniej. To wygoda, która "
                "wymaga jednak krótkiej adaptacji.</p>"
                "<h2>Ile trwa adaptacja</h2>"
                "<p>Większość osób przyzwyczaja się w ciągu 3–7 dni regularnego "
                "noszenia. U niektórych pełny komfort pojawia się dopiero po dwóch "
                "tygodniach — i to wciąż mieści się w normie.</p>"
                "<h2>Jakie objawy są normalne</h2>"
                "<ul>"
                "<li>Lekkie zniekształcenia na brzegach soczewki</li>"
                "<li>Potrzeba świadomego ruchu głową zamiast samych oczu</li>"
                "<li>Chwilowe uczucie „falowania” podłoża przy schodach</li>"
                "</ul>"
                "<h2>Kiedy skonsultować się z optometrystą</h2>"
                "<p>Jeśli po dwóch tygodniach nadal odczuwasz ból głowy, zawroty "
                "głowy lub wyraźne rozmycie obrazu, wróć do gabinetu — może być "
                "potrzebna korekta doboru soczewek.</p>"
            ),
            "cover_image_alt": "Osoba przymierzająca okulary progresywne w gabinecie optycznym",
            "meta_title": "Okulary progresywne — adaptacja | okowFormie",
            "meta_description": (
                "Okulary progresywne wymagają czasu na adaptację. Dowiedz się, ile "
                "trwa przyzwyczajenie, jakie objawy są normalne i kiedy warto "
                "skonsultować się z optometrystą."
            ),
            "published_days_ago": 7,
        },
    },
)


def _placeholder_image(
    *, text: str, size: tuple[int, int], background: tuple[int, int, int]
) -> ContentFile:
    """Wygeneruj prosty obraz JPEG z wyśrodkowanym podpisem.

    Placeholder programistyczny (Pillow), nie plik z repo — `seed_demo_data`
    nie ma commitować żadnych binarek (`.claude/rules/security.md`). Musi
    przejść `core.validators.validate_image_upload`: prawdziwa treść obrazu
    weryfikowalna przez `Image.open(...).verify()`, poniżej limitu rozmiaru.
    """
    image = Image.new("RGB", size, color=background)
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()

    lines = textwrap.wrap(text, width=24) or [text]
    line_sizes = [draw.textbbox((0, 0), line, font=font)[2:4] for line in lines]
    line_gap = 8
    total_height = sum(height for _, height in line_sizes) + line_gap * (len(lines) - 1)

    y = (size[1] - total_height) // 2
    for line, (width, height) in zip(lines, line_sizes, strict=True):
        x = (size[0] - width) // 2
        draw.text((x, y), line, font=font, fill=(255, 255, 255))
        y += height + line_gap

    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=85)
    return ContentFile(buffer.getvalue())


class Command(BaseCommand):
    help = "Wypełnij bazę danymi demo (autor, „O mnie”, certyfikaty, posty) dla frontendu."

    def handle(self, *args: Any, **options: Any) -> None:
        author = self._seed_author()
        about = self._seed_about()
        self._seed_certificates(about)
        self._seed_posts(author)
        self.stdout.write(self.style.SUCCESS("Seed danych demo zakończony."))

    def _seed_author(self) -> User:
        user, created = User.objects.get_or_create(
            username=DEMO_AUTHOR_USERNAME,
            defaults={
                "email": DEMO_AUTHOR_EMAIL,
                "first_name": DEMO_AUTHOR_FIRST_NAME,
                "last_name": DEMO_AUTHOR_LAST_NAME,
                "is_staff": True,
            },
        )
        if created:
            # Konto demo nie służy do logowania — brak hasła zamyka tę drogę
            # zamiast zostawiać przewidywalny sekret (`.claude/rules/security.md`).
            user.set_unusable_password()
            user.save(update_fields=["password"])
            self.stdout.write(self.style.SUCCESS(f"Utworzono konto redakcyjne „{user.username}”."))
        else:
            self.stdout.write(f"Konto redakcyjne „{user.username}” już istnieje — pomijam.")
        return user

    def _seed_about(self) -> AboutMe:
        about, created = AboutMe.objects.get_or_create(
            pk=AboutMe.SINGLETON_ID,
            defaults={"full_name": ABOUT_FULL_NAME},
        )
        if created:
            about.photo.save(
                "anna-kowalska.jpg",
                _placeholder_image(
                    text=ABOUT_FULL_NAME, size=(800, 800), background=ABOUT_PHOTO_COLOR
                ),
                save=True,
            )
            self.stdout.write(self.style.SUCCESS("Utworzono stronę „O mnie”."))
        else:
            self.stdout.write("Strona „O mnie” już istnieje — pomijam dane wspólne.")

        for language_code, translation_data in ABOUT_TRANSLATIONS.items():
            _, translation_created = AboutMeTranslation.objects.get_or_create(
                master=about,
                language_code=language_code,
                defaults={**translation_data, "status": AboutStatus.PUBLISHED},
            )
            if translation_created:
                self.stdout.write(
                    self.style.SUCCESS(f"Utworzono tłumaczenie „O mnie” [{language_code}].")
                )
            else:
                self.stdout.write(f"Tłumaczenie „O mnie” [{language_code}] już istnieje — pomijam.")

        return about

    def _seed_certificates(self, about: AboutMe) -> None:
        for order, certificate_data in enumerate(CERTIFICATES):
            certificate, created = Certificate.objects.get_or_create(
                about=about,
                name=certificate_data["name"],
                defaults={
                    "issuer": certificate_data["issuer"],
                    "issued_year": certificate_data["issued_year"],
                    "order": order,
                },
            )
            if created:
                color = CERTIFICATE_COLORS[order % len(CERTIFICATE_COLORS)]
                certificate.image.save(
                    f"certyfikat-{order + 1}.jpg",
                    _placeholder_image(
                        text=certificate_data["name"], size=(640, 452), background=color
                    ),
                    save=True,
                )
                self.stdout.write(self.style.SUCCESS(f"Utworzono certyfikat „{certificate.name}”."))
            else:
                self.stdout.write(f"Certyfikat „{certificate.name}” już istnieje — pomijam.")

    def _seed_posts(self, author: User) -> None:
        for post_seed in POSTS:
            post = self._seed_post_pl(author, post_seed["pl"])

            translation_en = post_seed.get("en")
            if translation_en is not None:
                self._seed_post_translation(post, Language.EN, translation_en)

    def _seed_post_pl(self, author: User, translation_data: PostTranslationSeed) -> Post:
        existing = (
            PostTranslation.objects.select_related("master")
            .filter(language_code=Language.PL, slug=translation_data["slug"])
            .first()
        )
        if existing is not None:
            self.stdout.write(f"Post „{translation_data['title']}” już istnieje — pomijam.")
            return existing.master

        post = Post.objects.create(author=author)
        post.cover_image.save(
            f"{translation_data['slug']}.jpg",
            _placeholder_image(
                text=translation_data["title"], size=(1200, 630), background=POST_COVER_COLOR
            ),
            save=True,
        )
        self._create_post_translation(post, Language.PL, translation_data)
        self.stdout.write(self.style.SUCCESS(f"Utworzono post PL „{translation_data['title']}”."))
        return post

    def _seed_post_translation(
        self, post: Post, language_code: str, translation_data: PostTranslationSeed
    ) -> None:
        title = translation_data["title"]
        if PostTranslation.objects.filter(master=post, language_code=language_code).exists():
            self.stdout.write(f"Tłumaczenie [{language_code}] „{title}” już istnieje — pomijam.")
            return

        self._create_post_translation(post, language_code, translation_data)
        self.stdout.write(self.style.SUCCESS(f"Utworzono tłumaczenie [{language_code}] „{title}”."))

    def _create_post_translation(
        self, post: Post, language_code: str, translation_data: PostTranslationSeed
    ) -> None:
        published_at = timezone.now() - timedelta(days=translation_data["published_days_ago"])
        PostTranslation.objects.create(
            master=post,
            language_code=language_code,
            status=PostStatus.PUBLISHED,
            published_at=published_at,
            slug=translation_data["slug"],
            title=translation_data["title"],
            excerpt=translation_data["excerpt"],
            content=translation_data["content"],
            cover_image_alt=translation_data["cover_image_alt"],
            meta_title=translation_data["meta_title"],
            meta_description=translation_data["meta_description"],
        )
