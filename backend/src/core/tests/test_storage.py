"""`RandomFilenameUploadTo` — fabryka `upload_to` z losową nazwą pliku
(`.claude/rules/security.md`), współdzielona przez pola obrazu, które
powstają po tym, jak próg z `.claude/rules/engineering-principles.md`
("abstrakcja dopiero przy trzecim powtórzeniu") został przekroczony
(`branding.models.branding_logo_upload_to`, czwarte powtórzenie po
`blog`/`about`).
"""

import uuid

from django.db.migrations.serializer import serializer_factory

from core.storage import RandomFilenameUploadTo


def test_generuje_sciezke_w_podanym_katalogu_z_zachowanym_rozszerzeniem() -> None:
    upload_to = RandomFilenameUploadTo("branding/logo")

    path = upload_to(None, "moje zdjecie.JPG")  # type: ignore[arg-type]

    assert path.startswith("branding/logo/")
    assert path.endswith(".jpg")


def test_kazde_wywolanie_daje_inna_losowa_nazwe() -> None:
    upload_to = RandomFilenameUploadTo("branding/logo")

    first = upload_to(None, "logo.png")  # type: ignore[arg-type]
    second = upload_to(None, "logo.png")  # type: ignore[arg-type]

    assert first != second


def test_brak_rozszerzenia_daje_sama_losowa_nazwe_bez_kropki() -> None:
    upload_to = RandomFilenameUploadTo("branding/logo")

    path = upload_to(None, "bez_rozszerzenia")  # type: ignore[arg-type]

    filename = path.removeprefix("branding/logo/")
    assert uuid.UUID(hex=filename)


def test_deconstructible_pozwala_zserializowac_instancje_w_migracji() -> None:
    """Regresja dla defektu z `/code-review`: funkcja fabrykująca zwracająca
    zwykłe domknięcie (`def upload_to(...): ...` zagnieżdżone w innej
    funkcji) nie daje się zserializować w migracji Django —
    `FunctionTypeSerializer` jawnie odrzuca `__qualname__` zawierający
    `<locals>`. `@deconstructible` naprawia to, dając instancji `deconstruct()`
    — sprawdzamy to bezpośrednio przez serializer migracji, tak jak zrobiłby
    to `makemigrations`."""
    upload_to = RandomFilenameUploadTo("branding/logo")

    serialized, imports = serializer_factory(upload_to).serialize()

    assert serialized == "core.storage.RandomFilenameUploadTo('branding/logo')"
    assert "import core.storage" in imports
