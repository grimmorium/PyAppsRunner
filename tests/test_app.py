"""Testy pętli głównej aplikacji - App łączy nawigację, renderer i runner (Krok 8).

Wszystkie testy używają wstrzykiwanego I/O: FakeKeyReader zamiast klawiatury,
io.StringIO zamiast terminala oraz rekordery clear/pause/size. Domyślnie
używany jest prawdziwy run_script (skrypty z fixture tmp_project).
"""

import io
from pathlib import Path
from types import SimpleNamespace

from menu_app.app import App
from menu_app.config import load_menu
from menu_app.keys import Key
from menu_app.runner import RunResult, run_script
from menu_app.testing import FakeKeyReader
from menu_app.texts import (
    ERR_SCRIPT_NOT_FOUND,
    ERR_SCRIPT_OUTSIDE_BASE,
    FOOTER_TEXT,
    PRESS_ENTER,
    SCRIPT_ERROR_WITH_CODE,
)

# Separator zapisywany przez fake'owy clear() - pozwala rozdzielić ekrany w out.
SCREEN_SEP = "\x00SCR\x00"


def make_app(project: Path, keys, script_runner=None) -> SimpleNamespace:
    """Buduje App z kontrolowanym I/O; zwraca harness (app + rekordery)."""
    root = load_menu(project / "menu.xml")
    out = io.StringIO()
    h = SimpleNamespace(app=None, out=out, contexts=[], pauses=[], clears=[], sizes=[])

    def runner(ctx):
        h.contexts.append(ctx)
        return run_script(ctx) if script_runner is None else script_runner(ctx)

    def clear(stream: object) -> None:
        h.clears.append(stream)
        stream.write(SCREEN_SEP)  # type: ignore[union-attr]

    def get_size():
        size = (80, 24)
        h.sizes.append(size)
        return size

    h.app = App(
        root=root,
        base_dir=project,
        key_reader=FakeKeyReader(keys),
        out=out,
        script_runner=runner,
        pause=lambda: h.pauses.append(None),
        size_provider=get_size,
        clear=clear,
    )
    return h


def screens(h: SimpleNamespace) -> list[str]:
    """Poszczególne narysowane ekrany (po separatorze z fake'owego clear)."""
    return [p for p in h.out.getvalue().split(SCREEN_SEP) if p.strip()]


# Drzewo fixture tmp_project (root): Znacznik(0), Błęd demo(1), Narzędzia(2), Wyjście(3)

def test_enter_on_exit_returns_zero(tmp_project: Path) -> None:
    h = make_app(tmp_project, [Key.DOWN] * 3 + [Key.ENTER])
    assert h.app.run() == 0
    assert h.contexts == []      # żaden skrypt nie został uruchomiony
    assert h.pauses == []


def test_run_first_item_passes_correct_context(tmp_project: Path) -> None:
    # pierwsza pozycja ("Znacznik" -> marker.py) aktywowana od razu; potem wyjście
    keys = [Key.ENTER] + [Key.DOWN, Key.DOWN, Key.DOWN, Key.ENTER]
    h = make_app(tmp_project, keys)
    rc = h.app.run()
    assert rc == 0
    assert len(h.contexts) == 1
    ctx = h.contexts[0]
    expected_path = (tmp_project / "scripts" / "basic" / "marker.py").resolve()
    assert ctx.script_path == expected_path
    assert ctx.base_dir.resolve() == tmp_project.resolve()
    assert ctx.script_dir == expected_path.parent
    assert ctx.menu_path == ()  # aktywowano pozycję z poziomu roota


def test_pause_called_with_message_by_default(tmp_project: Path) -> None:
    # marker.py (pierwsza pozycja) zwraca 0 -> sukces; potem wyjście
    keys = [Key.ENTER] + [Key.DOWN, Key.DOWN, Key.DOWN, Key.ENTER]
    h = make_app(tmp_project, keys)
    assert h.app.run() == 0
    assert len(h.pauses) == 1
    assert PRESS_ENTER in h.out.getvalue()


def test_skip_pause_skips_pause_and_message(tmp_project: Path) -> None:
    def runner(ctx):  # skrypt "prosi" o pominięcie pauzy
        return RunResult(ok=True, skip_pause=True)

    keys = [Key.ENTER] + [Key.DOWN, Key.DOWN, Key.DOWN, Key.ENTER]
    h = make_app(tmp_project, keys, script_runner=runner)
    assert h.app.run() == 0
    assert h.pauses == []
    assert PRESS_ENTER not in h.out.getvalue()


def test_subfolder_and_back_restores_selection(tmp_project: Path) -> None:
    # root(2)=Narzędzia -> Głęboko -> Wstecz x2 (z przywróconym zaznaczeniem) -> wyjście
    keys = [
        Key.DOWN, Key.DOWN, Key.ENTER,   # root: sel 2 (Narzędzia), wejście
        Key.ENTER,                        # Narzędzia: wejście do Głęboko (sel 0)
        Key.DOWN, Key.DOWN, Key.ENTER,    # Głęboko ma 3 pozycje -> Wstecz na końcu
        Key.DOWN, Key.ENTER,              # Narzędzia: Wstecz (root, sel przywrócone = 2)
        Key.DOWN, Key.ENTER,              # root: Wyjście
    ]
    h = make_app(tmp_project, keys)
    assert h.app.run() == 0

    headers = [s.splitlines()[0] for s in screens(h)]
    assert "Menu testowe / Narzędzia" in headers
    deep_idx = headers.index("Menu testowe / Narzędzia / Głęboko")
    back_to_root_after_deep = [i for i, x in enumerate(headers) if x == "Menu testowe" and i > deep_idx]
    assert back_to_root_after_deep, "po Wstecz x2 ekran roota się pojawił"

    # po powrocie do roota zaznaczenie musi być przywrócone na Narzędzia (indeks 2)
    first_back_screen = screens(h)[back_to_root_after_deep[0]]
    assert "> Narzędzia" in first_back_screen
    assert "> Znacznik" not in first_back_screen


def test_exit_to_root_after_script(tmp_project: Path) -> None:
    def runner(ctx):
        return RunResult(ok=True, exit_to_root=True, skip_pause=True)

    # root -> Narzędzia -> Głęboko -> "Do roota"; po skrypcie ekran roota, potem wyjście
    keys = [
        Key.DOWN, Key.DOWN, Key.ENTER,   # Narzędzia
        Key.ENTER,                        # Głęboko (zaznaczenie 0 = Do roota)
        Key.ENTER,                        # uruchomienie skryptu
        Key.DOWN, Key.DOWN, Key.DOWN, Key.ENTER,  # z roota: 3x dół -> Wyjście
    ]
    h = make_app(tmp_project, keys, script_runner=runner)
    assert h.app.run() == 0          # gdyby go_root nie zadziałał, skończyłyby się klawisze
    assert len(h.contexts) == 1      # ...a drugi ENTER aktywowałby ten sam skrypt ponownie
    headers = [s.splitlines()[0] for s in screens(h)]
    deep_idx = headers.index("Menu testowe / Narzędzia / Głęboko")
    assert "Menu testowe" in headers[deep_idx + 1:]


def test_error_result_printed_and_menu_continues(tmp_project: Path) -> None:
    def runner(ctx):
        return RunResult(ok=False, return_code=3, error="RuntimeError: Celowy błąd testowy")

    keys = [Key.DOWN, Key.ENTER] + [Key.DOWN, Key.DOWN, Key.ENTER]  # potem wyjście
    h = make_app(tmp_project, keys, script_runner=runner)
    assert h.app.run() == 0
    expected = SCRIPT_ERROR_WITH_CODE.format(error="RuntimeError: Celowy błąd testowy", code=3)
    assert expected in h.out.getvalue()
    assert len(h.pauses) == 1  # pauza także po błędnym skrypcie


def test_missing_and_outside_base_scripts_reported(tmp_path: Path) -> None:
    xml = (
        "<?xml version=\"1.0\" encoding=\"utf-8\"?>\n"
        "<menu title=\"T\">\n"
        '  <item name="Brak" dir="scripts" file="brak.py"/>\n'
        '  <item name="Zewnatrz" dir="../x" file="y.py"/>\n'
        "</menu>\n"
    )
    (tmp_path / "menu.xml").write_text(xml, encoding="utf-8")
    # Brak(0) -> błąd braku pliku; Zewnatrz(1) -> błąd poza bazą; potem Wyjście.
    # Po błędzie zaznaczenie zostaje na pozycji skryptu (stan menu się nie zmienia).
    keys = [Key.ENTER, Key.DOWN, Key.ENTER, Key.DOWN, Key.ENTER]
    h = make_app(tmp_path, keys)  # runner nie powinien być wywołany ani razu
    assert h.app.run() == 0
    text = h.out.getvalue()
    assert ERR_SCRIPT_OUTSIDE_BASE.partition(":")[0] in text
    assert ERR_SCRIPT_NOT_FOUND.partition(":")[0] in text  # brakujący plik (stała z texts.py)
    assert h.contexts == []


def test_other_key_is_ignored(tmp_project: Path) -> None:
    keys = [Key.OTHER, Key.DOWN, Key.DOWN, Key.DOWN, Key.ENTER]
    h = make_app(tmp_project, keys)
    assert h.app.run() == 0
    assert h.contexts == []  # OTHER nie aktywował pierwszej pozycji
    assert h.pauses == []


def test_interrupt_returns_zero(tmp_project: Path) -> None:
    h = make_app(tmp_project, [Key.INTERRUPT])
    assert h.app.run() == 0
    assert h.contexts == []
    assert h.pauses == []


def test_screen_shows_labels_footer_and_selection(tmp_project: Path) -> None:
    h = make_app(tmp_project, [Key.INTERRUPT])
    assert h.app.run() == 0
    text = screens(h)[0]
    lines = text.splitlines()
    assert lines[0] == "Menu testowe"
    assert "> Znacznik" in text      # zaznaczona pierwsza pozycja
    assert "Błęd demo" in text       # pozostałe etykiety z XML-a
    assert "Narzędzia" in text
    assert "Wyjście" in text         # pozycja systemowa roota
    assert FOOTER_TEXT in text


def test_clear_and_size_provider_receives_expected_arguments(tmp_project: Path) -> None:
    h = make_app(tmp_project, [Key.DOWN, Key.INTERRUPT])
    h.app.run()
    assert all(stream is h.out for stream in h.clears)
    assert len(h.clears) >= 1        # czyszczenie przed każdym ekranem
    assert set(h.sizes) == {(80, 24)}
