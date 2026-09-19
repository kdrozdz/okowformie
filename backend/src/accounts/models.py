from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """Własny model użytkownika.

    Pusty w fazie 1 (celowo — YAGNI). Istnieje od pierwszej migracji zgodnie
    z zasadą przyszłościową w `.claude/rules/scope.md`: konta redakcyjne
    (staff, faza 1) i przyszłe konta klientów (faza 2) mają współdzielić ten
    sam model, rozróżniany rolami — podmiana `AUTH_USER_MODEL` po fakcie
    byłaby kosztowną migracją.
    """
