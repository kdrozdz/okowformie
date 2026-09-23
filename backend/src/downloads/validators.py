"""Walidator uploadu pliku do pobrania.

Pierwsze (i na razie jedyne) użycie tego kształtu walidacji — zostaje tutaj,
w `downloads`, zamiast w `core`. Próg wydzielenia do miejsca współdzielonego
to trzecie powtórzenie (`.claude/rules/engineering-principles.md`), inaczej
niż `core.validators.validate_image_upload`, które ma już trzy użycia
(`blog`, `about` x2) i faktycznie jest reużywane, nie tylko potencjalnie
reużywalne.

`.claude/rules/security.md`: walidacja rozszerzenia, rozmiaru i **realnej
zawartości** — nigdy nie ufamy samemu rozszerzeniu ani nagłówkowi
`Content-Type` z requestu (ten ostatni w ogóle nie dociera do walidatora
pola modelu, ale rozszerzenie samo w sobie jest równie łatwe do podrobienia).
PDF zaczyna się zawsze od magic bytes `%PDF-` (specyfikacja PDF, ISO 32000,
nagłówek pliku) — sprawdzenie pierwszych pięciu bajtów odróżnia prawdziwy
dokument od dowolnego innego pliku podszywającego się pod to rozszerzenie.
"""

from pathlib import Path
from typing import Final

from django.core.exceptions import ValidationError
from django.core.files.base import File

#: Jedyny dozwolony typ pliku na start (`docs/tasks/16-pliki-do-pobrania.md`
#: — decyzja wejściowa, YAGNI: rozszerzalne później, gdy pojawi się potrzeba).
ALLOWED_EXTENSIONS: Final[frozenset[str]] = frozenset({".pdf"})

#: 10 MB — wystarcza na skan/dokument tekstowy, a jednocześnie nie pozwala
#: wgrać czegoś, co w praktyce nie nadaje się do pobrania na wolniejszym łączu.
MAX_FILE_BYTES: Final[int] = 10 * 1024 * 1024

_PDF_MAGIC_BYTES: Final[bytes] = b"%PDF-"


def validate_pdf_upload(value: File) -> None:
    """Sprawdź rozszerzenie, rozmiar i faktyczną zawartość przesłanego pliku."""
    extension = Path(value.name or "").suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise ValidationError(
            "Ten format pliku nie jest obsługiwany. Zapisz plik jako PDF i wgraj ponownie.",
            code="invalid_file_extension",
        )

    if value.size is not None and value.size > MAX_FILE_BYTES:
        raise ValidationError(
            "Plik waży %(size).1f MB, a maksimum to %(limit)d MB. Zmniejsz plik "
            "(np. skompresuj PDF) i wgraj ponownie.",
            code="file_too_large",
            params={
                "size": value.size / (1024 * 1024),
                "limit": MAX_FILE_BYTES // (1024 * 1024),
            },
        )

    _validate_pdf_content(value)


def _validate_pdf_content(value: File) -> None:
    """Odrzuć plik, którego treść nie zaczyna się od nagłówka PDF, mimo że
    rozszerzenie jest prawidłowe (np. dowolny inny plik zapisany jako `.pdf`).

    Czyta tylko pierwsze pięć bajtów i cofa wskaźnik pliku do pozycji
    wyjściowej — bez tego dalszy odczyt tego samego uchwytu (np. faktyczny
    zapis na storage zaraz po walidacji) dostałby plik "nadgryziony" od
    początku, tak samo jak w `core.validators._validate_image_content`.
    """
    position = value.tell() if hasattr(value, "tell") else 0
    try:
        header = value.read(len(_PDF_MAGIC_BYTES))
    finally:
        if hasattr(value, "seek"):
            value.seek(position)

    if header != _PDF_MAGIC_BYTES:
        raise ValidationError(
            "Ten plik nie jest poprawnym dokumentem PDF, mimo że rozszerzenie "
            "jest prawidłowe. Wgraj prawdziwy plik PDF.",
            code="invalid_file_content",
        )
