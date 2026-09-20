"""Normalizacja orientacji EXIF przesyłanych obrazów.

Telefony zapisują zdjęcia w orientacji „surowej" (piksele tak, jak trafiły z
sensora) i dokładają flagę EXIF `Orientation` mówiącą odbiorcy, jak obrócić
obraz przy wyświetlaniu. `<img>` na stronie zwykle tę flagę respektuje, ale
nie każdy konsument tego samego pliku już tak — np. favicon serwowany jako
surowe bajty (`frontend/src/app/icon.tsx`) często ją ignoruje, więc ten sam
plik wygląda poprawnie w jednym miejscu i obrócony w drugim.

Zamiast polegać na tym, że każdy konsument poprawnie zinterpretuje EXIF,
obracamy piksele raz, przy zapisie, i usuwamy samą flagę — każdy kolejny
odbiorca dostaje już poprawnie zorientowany obraz bez żadnej specjalnej
obsługi po swojej stronie.
"""

from io import BytesIO
from pathlib import Path

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import UploadedFile
from PIL import Image, ImageOps

#: Jakość zapisu przy ponownym kodowaniu JPEG — wysoka, ale nie 100 (brak
#: praktycznej różnicy jakości, zauważalny wzrost rozmiaru pliku).
_JPEG_SAVE_QUALITY = 90

#: Format zapisu Pillow do użycia dla każdego dozwolonego rozszerzenia
#: (`core.validators.ALLOWED_IMAGE_EXTENSIONS`). Wybór formatu na podstawie
#: rozszerzenia, nie `image.format` introspekcji Pillow — telefony z
#: podwójną kamerą/3D bywają eksportują `.jpg` jako kontener Pillow `"MPO"`
#: (multi-picture JPEG), który przechodzi walidację rozszerzenia, ale nie
#: trafiłby w gałąź `== "JPEG"` niżej i dostałby domyślną (niższą) jakość
#: zapisu Pillow.
_FORMAT_BY_EXTENSION: dict[str, str] = {
    ".jpg": "JPEG",
    ".jpeg": "JPEG",
    ".png": "PNG",
    ".webp": "WEBP",
}


def normalize_image_orientation(uploaded_file: UploadedFile) -> ContentFile:
    """Obróć piksele zgodnie z EXIF `Orientation` i usuń tę flagę.

    Zwraca nowy plik w pamięci — nie mutuje `uploaded_file`. Obrazy bez flagi
    `Orientation` (typowe dla PNG/WebP, część JPEG-ów) przechodzą przez
    `ImageOps.exif_transpose` bez zmiany pikseli — funkcja jest wtedy no-opem
    poza ponownym zakodowaniem pliku.

    `core.validators.validate_image_upload` (wołany wcześniej, na poziomie
    walidatora pola) sprawdza treść pliku tylko przez `Image.open(...).verify()`,
    który nie robi pełnego decode pikseli — plik przechodzący `.verify()` może
    więc mimo to wysypać dekodowanie/re-encode tutaj. Zamieniamy taki wyjątek
    Pillow na `ValidationError`, żeby dostać czytelny komunikat/log zamiast
    surowego tracebacku Pillow (ten sam wzorzec co
    `core.validators._validate_image_content`).
    """
    uploaded_file.seek(0)
    try:
        image = Image.open(uploaded_file)
        extension = Path(uploaded_file.name or "").suffix.lower()
        image_format = _FORMAT_BY_EXTENSION.get(extension, image.format or "JPEG")
        transposed = ImageOps.exif_transpose(image)

        buffer = BytesIO()
        save_kwargs: dict[str, object] = {}
        if image_format == "JPEG":
            # `exif_transpose` może zwrócić obraz w trybie niekompatybilnym z
            # zapisem JPEG (np. paleta/alfa) — JPEG nie ma kanału alfa,
            # PNG/WebP poniżej same sobie z tym radzą.
            if transposed.mode not in ("RGB", "L"):
                transposed = transposed.convert("RGB")
            save_kwargs["quality"] = _JPEG_SAVE_QUALITY

        transposed.save(buffer, format=image_format, **save_kwargs)
    except Exception as exc:
        raise ValidationError(
            "Nie udało się przetworzyć tego obrazu. Wgraj prawdziwe zdjęcie w "
            "formacie JPG, PNG lub WebP.",
            code="invalid_image_content",
        ) from exc

    buffer.seek(0)
    return ContentFile(buffer.read(), name=uploaded_file.name)
