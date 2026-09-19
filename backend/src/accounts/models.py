from typing import TYPE_CHECKING

from django.contrib.auth.models import AbstractUser

if TYPE_CHECKING:
    from django.db.models.fields.related_descriptors import RelatedManager

    from blog.models import Post


class User(AbstractUser):
    """Własny model użytkownika.

    Pusty w fazie 1 (celowo — YAGNI). Istnieje od pierwszej migracji zgodnie
    z zasadą przyszłościową w `.claude/rules/scope.md`: konta redakcyjne
    (staff, faza 1) i przyszłe konta klientów (faza 2) mają współdzielić ten
    sam model, rozróżniany rolami — podmiana `AUTH_USER_MODEL` po fakcie
    byłaby kosztowną migracją.
    """

    if TYPE_CHECKING:
        # Relacja odwrotna z `blog.Post.author`. Deklaracja tylko dla mypy —
        # w runtime tworzy ją Django. Bez niej `django-stubs` nie potrafi
        # rozwiązać menedżera i zgłasza `django-manager-missing`.
        posts: RelatedManager[Post]
