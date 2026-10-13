"""Testy budowy tekstu ekranu menu - czysta funkcja (Krok 6 specyfikacji)."""

from menu_app.renderer import render_screen
from menu_app.texts import FOOTER_TEXT


def _lines(screen: str) -> list[str]:
    return screen.split("\n")[:-1] if screen.endswith("\n") else screen.split("\n")


def test_selected_row_has_prefix_and_is_unique() -> None:
    screen = render_screen("Tytuł", (), ["Alfa", "Beta", "Gama"], 1, 80, 24)
    lines = _lines(screen)
    assert lines[0] == "Tytuł"
    assert lines[2] == "  Alfa"
    assert lines[3] == "> Beta"
    assert lines[4] == "  Gama"
    selected_rows = [line for line in lines if line.startswith("> ")]
    assert len(selected_rows) == 1


def test_breadcrumb_in_header() -> None:
    screen = render_screen("Główne", ("Narzędzia", "Zaawansowane"), ["x"], 0, 80, 24)
    lines = _lines(screen)
    assert lines[0] == "Główne / Narzędzia / Zaawansowane"


def test_separator_length() -> None:
    wide = _lines(render_screen("T", (), ["a"], 0, 80, 24))
    assert wide[1] == "-" * 40                       # min(width, 40)
    narrow = _lines(render_screen("T", (), ["a"], 0, 20, 24))
    assert narrow[1] == "-" * 20


def test_blank_line_before_footer() -> None:
    lines = _lines(render_screen("T", (), ["a", "b"], 0, 80, 24))
    assert lines[-1] == FOOTER_TEXT
    assert lines[-2] == ""


LABELS_50 = [f"pozycja {i}" for i in range(50)]


def test_scrolling_selected_always_visible() -> None:
    for selected in (0, 25, 49):
        screen = render_screen("T", (), LABELS_50, selected, 80, 10)
        lines = _lines(screen)
        assert f"> pozycja {selected}" in lines


def test_scrolling_indicators_in_right_places() -> None:
    # na początku listy: brak wskaźnika u góry, wskaźnik na dole
    top_lines = _lines(render_screen("T", (), LABELS_50, 0, 80, 10))
    area_top = [l for l in top_lines[2:-2]]          # bez nagłówków i stopki
    assert area_top[0] == "> pozycja 0"
    assert "  ..." not in (area_top[0],)
    assert area_top[-1] == "  ..."

    # na końcu listy: wskaźnik u góry, brak na dole
    bottom_lines = _lines(render_screen("T", (), LABELS_50, 49, 80, 10))
    area_bottom = [l for l in bottom_lines[2:-2]]
    assert area_bottom[-1] == "> pozycja 49"
    assert area_bottom[0] == "  ..."

    # w środku: wskaźniki z obu stron
    middle_lines = _lines(render_screen("T", (), LABELS_50, 25, 80, 10))
    area_middle = [l for l in middle_lines[2:-2]]
    assert area_middle[0] == "  ..."
    assert area_middle[-1] == "  ..."


def test_scrolling_respects_height_limit() -> None:
    for selected in (0, 25, 49):
        lines = _lines(render_screen("T", (), LABELS_50, selected, 80, 10))
        assert len(lines) <= 10


def test_long_label_truncated_with_ellipsis() -> None:
    long_label = "x" * 60
    screen = render_screen("Tytuł bardzo długi ponad szerokość okna", (), [long_label], 0, 30, 24)
    lines = _lines(screen)
    assert len(lines[0]) <= 30
    assert lines[0].endswith("…")
    row = lines[2]
    assert len(row) <= 30
    assert row.startswith("> ")
    assert row.endswith("…")


def test_no_exception_on_tiny_windows() -> None:
    for width, height in ((5, 3), (8, 4), (10, 6), (99, 2)):
        screen = render_screen("T", (), ["a", "b"], 1, width, height)
        assert isinstance(screen, str)


def test_polish_characters_survive() -> None:
    screen = render_screen("Żółw", ("Ślimak",), ["ż ę ł ż ą ć ń ó ś ź ć"], 0, 80, 24)
    assert "Żółw / Ślimak" in screen
    assert "> ż ę ł ż ą ć ń ó ś ź ć" in screen
