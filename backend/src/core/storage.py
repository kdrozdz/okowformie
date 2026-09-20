"""Fabryka `upload_to` dla pól obrazu z losową nazwą pliku.

Ten sam dwuliniowy wzorzec (`suffix` z nazwy uploadu + losowa nazwa pliku +
stały katalog) już istnieje trzykrotnie: `blog.models.post_cover_upload_to`,
`about.models.about_photo_upload_to`, `about.models.certificate_image_upload_to`.
`branding.models` jest czwartym powtórzeniem — próg z
`.claude/rules/engineering-principles.md` ("abstrakcja dopiero przy trzecim
powtórzeniu") jest przekroczony, więc dla `branding` (i wszystkiego nowego)
ścieżkę generuje ta wspólna fabryka.

`blog`/`about` świadomie NIE zostały zretrofitowane w tym tasku — ich funkcje
`upload_to` są referencjonowane po ścieżce importu w już zaaplikowanych
migracjach (`blog/migrations/0001_initial.py`, `about/migrations/...`);
przepięcie ich na tę fabrykę wymagałoby nowej migracji dla apek już wdrożonych
w innej gałęzi/fazie, co wykracza poza zakres tego brancha
(`.claude/rules/engineering-principles.md`: „Kiedy się zatrzymać i zapytać" —
zmiana schematu spoza zakresu). To kandydat do osobnego, jawnie zleconego
taska porządkowego.
"""

import uuid
from pathlib import Path

from django.db.models import Model
from django.utils.deconstruct import deconstructible


@deconstructible
class RandomFilenameUploadTo:
    """Callable `upload_to`: zapisuje plik pod losową nazwą w `directory`.

    Klasa, nie funkcja zwracająca domknięcie (closure) — celowo. Referencja
    do `upload_to` pola `ImageField`/`FileField` jest serializowana w treści
    migracji Django, a `django.db.migrations.serializer.FunctionTypeSerializer`
    jawnie odrzuca funkcje zagnieżdżone: ich `__qualname__` zawiera
    `<locals>`, czego serializer nie potrafi zapisać jako importowalną ścieżkę
    (`ValueError: Could not find function ...`) — sprawdzone przez
    `manage.py makemigrations` przy pierwszej próbie z funkcją fabrykującą
    zwracającą `def upload_to(...)`.

    `@deconstructible` to udokumentowany wzorzec Django właśnie na ten
    przypadek: instancja zapisuje się w migracji jako wywołanie konstruktora
    z argumentami (`core.storage.RandomFilenameUploadTo("branding/logo")`),
    więc `makemigrations`/`migrate` działają bez dodatkowego kodu.
    """

    def __init__(self, directory: str) -> None:
        self.directory = directory

    def __call__(self, instance: Model, filename: str) -> str:
        extension = Path(filename).suffix.lower()
        return f"{self.directory}/{uuid.uuid4().hex}{extension}"
