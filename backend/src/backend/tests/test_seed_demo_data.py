"""`seed_demo_data` (`backend/src/backend/management/commands/seed_demo_data.py`).

Nie testujemy treści seeda słowo w słowo (to dane demo, mogą się zmieniać) —
tylko kontrakt, na którym polega frontend i workflow developerski:
komenda się uruchamia bez błędu i jest idempotentna (drugie wywołanie nie
mnoży rekordów ani obrazów). Wzorowane na `about/tests/test_api_about.py` /
`blog/tests/test_api_posts.py` co do stylu (pytest-django, nazwy testów po
polsku, `pytestmark = pytest.mark.django_db`).
"""

import pytest
from django.core.management import call_command

from about.models import AboutMe, AboutMeTranslation, Certificate
from accounts.models import User
from blog.models import Post, PostTranslation

pytestmark = pytest.mark.django_db


def _run_seed() -> None:
    call_command("seed_demo_data")


def test_seed_uruchamia_sie_bez_bledu_i_tworzy_dane() -> None:
    _run_seed()

    assert User.objects.filter(username="demo-author").exists()
    assert AboutMe.objects.count() == 1
    assert AboutMeTranslation.objects.count() == 2  # PL + EN
    assert Certificate.objects.count() == 8
    assert Post.objects.count() == 10
    # co najmniej jeden post ma tłumaczenie EN (wymóg planu taska)
    assert PostTranslation.objects.filter(language_code="en").exists()


def test_seed_jest_idempotentny() -> None:
    _run_seed()

    users_before = User.objects.count()
    about_before = AboutMe.objects.count()
    about_translations_before = AboutMeTranslation.objects.count()
    certificates_before = Certificate.objects.count()
    posts_before = Post.objects.count()
    post_translations_before = PostTranslation.objects.count()

    _run_seed()

    assert User.objects.count() == users_before
    assert AboutMe.objects.count() == about_before
    assert AboutMeTranslation.objects.count() == about_translations_before
    assert Certificate.objects.count() == certificates_before
    assert Post.objects.count() == posts_before
    assert PostTranslation.objects.count() == post_translations_before


def test_seed_nie_tworzy_uzytkownika_z_uzywalnym_haslem() -> None:
    """Konto demo nie ma służyć do logowania (`.claude/rules/security.md`)."""
    _run_seed()

    author = User.objects.get(username="demo-author")
    assert author.has_usable_password() is False
