"""Edytor bio nie może produkować HTML-a, który sanityzacja wyrzuci.

Ten sam niezmiennik co `blog/tests/test_editor_config.py`, sprawdzony
niezależnie dla `about.models.BIO_CONTENT_EXTENSIONS` — konfiguracja jest
świadomą kopią (`about/models.py`), więc może rozjechać się z allowlistą bez
tego, żeby test w `blog/` to złapał.
"""

import warnings
from typing import Any

from django_prose_editor.config import allowlist_from_extensions, expand_extensions

from about.models import BIO_CONTENT_EXTENSIONS
from core.sanitization import ALLOWED_ATTRIBUTES, ALLOWED_TAGS

#: `rel` jest świadomie poza allowlistą: nh3 nadpisuje go wartością
#: `LINK_REL`, więc redaktor nie może go osłabić.
ATTRIBUTES_MANAGED_BY_SANITIZER = {("a", "rel")}


def editor_allowlist() -> dict[str, Any]:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return allowlist_from_extensions(expand_extensions(BIO_CONTENT_EXTENSIONS))


def test_kazdy_tag_z_edytora_przechodzi_przez_sanityzacje() -> None:
    editor_tags: set[str] = set(editor_allowlist()["tags"])

    assert editor_tags <= set(ALLOWED_TAGS), sorted(editor_tags - set(ALLOWED_TAGS))


def test_kazdy_atrybut_z_edytora_przechodzi_przez_sanityzacje() -> None:
    editor_attributes: dict[str, set[str]] = editor_allowlist()["attributes"]

    missing = {
        (tag, attribute)
        for tag, attributes in editor_attributes.items()
        for attribute in attributes
        if attribute not in ALLOWED_ATTRIBUTES.get(tag, set())
    } - ATTRIBUTES_MANAGED_BY_SANITIZER

    assert not missing, sorted(missing)
