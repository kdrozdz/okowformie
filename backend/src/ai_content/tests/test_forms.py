"""`PostGenerationForm`: walidacja `topic`/`local_focus` (wymagane pole,
`max_length`, wartość domyślna) — nieprzetestowana dotąd bezpośrednio,
tylko pośrednio przez `test_admin.py` (droga HTTP przez `PostGeneratorAdmin`).

Obowiązkowy przypadek brzegowy formularzy panelu (`.claude/rules/
conventions.md`): pole wymagane bez wartości i bardzo długi tekst muszą
dawać czytelny błąd po polsku, nie generyczny komunikat Django ani
`DataError` z bazy dalej w łańcuchu."""

from ai_content.forms import PostGenerationForm


def test_formularz_z_poprawnymi_danymi_jest_valid() -> None:
    form = PostGenerationForm(
        data={"topic": "Soczewki kontaktowe", "local_focus": "Wrocław, Polska"}
    )

    assert form.is_valid(), form.errors


def test_local_focus_ma_domyslna_wartosc_wroclaw() -> None:
    """`initial="Wrocław, Polska"` — prefill widoczny na pustym formularzu (GET),
    nie wymuszany przy braku danych w POST (`initial` nie podstawia się za
    brakujące dane przy walidacji)."""
    form = PostGenerationForm()

    assert form.fields["local_focus"].initial == "Wrocław, Polska"


def test_topic_pusty_jest_odrzucany_z_polskim_komunikatem() -> None:
    form = PostGenerationForm(data={"topic": "", "local_focus": "Wrocław, Polska"})

    assert not form.is_valid()
    message = " ".join(str(e) for e in form.errors["topic"])
    assert "Temat jest wymagany" in message
    assert message != "To pole jest wymagane."


def test_local_focus_pusty_jest_odrzucany_z_polskim_komunikatem() -> None:
    form = PostGenerationForm(data={"topic": "Soczewki kontaktowe", "local_focus": ""})

    assert not form.is_valid()
    message = " ".join(str(e) for e in form.errors["local_focus"])
    assert "Fokus lokalny jest wymagany" in message
    assert message != "To pole jest wymagane."


def test_topic_za_dlugi_jest_odrzucany_z_polskim_komunikatem() -> None:
    """`topic.max_length == 200` — obowiązkowy przypadek brzegowy."""
    form = PostGenerationForm(data={"topic": "a" * 201, "local_focus": "Wrocław, Polska"})

    assert not form.is_valid()
    message = " ".join(str(e) for e in form.errors["topic"])
    assert "Skróć go" in message
    assert "Upewnij się" not in message  # generyczny komunikat Django


def test_local_focus_za_dlugi_jest_odrzucany_z_polskim_komunikatem() -> None:
    form = PostGenerationForm(data={"topic": "Soczewki kontaktowe", "local_focus": "a" * 201})

    assert not form.is_valid()
    message = " ".join(str(e) for e in form.errors["local_focus"])
    assert "Skróć go" in message
    assert "Upewnij się" not in message


def test_topic_dokladnie_na_limicie_jest_akceptowany() -> None:
    """Granica `max_length` (200 znaków dokładnie) nie jest odrzucana —
    tylko wartości *powyżej* limitu."""
    form = PostGenerationForm(data={"topic": "a" * 200, "local_focus": "Wrocław, Polska"})

    assert form.is_valid(), form.errors
