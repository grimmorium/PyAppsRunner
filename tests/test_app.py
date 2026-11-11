"""Tests of the application main loop - App ties together navigation, renderer and runner (Step 8).

All tests use injected I/O: FakeKeyReader instead of a keyboard, io.StringIO
instead of a terminal, plus clear/pause/size recorders. The real run_script
is used by default (scripts from the tmp_project fixture).
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

# Separator written by the fake clear() - allows splitting screens in out.
SCREEN_SEP = "\x00SCR\x00"


def make_app(project: Path, keys, script_runner=None) -> SimpleNamespace:
    """Builds an App with controlled I/O; returns a harness (app + recorders)."""
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
    """Individual drawn screens (after the fake-clear separator)."""
    return [p for p in h.out.getvalue().split(SCREEN_SEP) if p.strip()]


# tmp_project fixture tree (root): Marker(0), Error demo(1), Tools(2), Exit(3)

def test_enter_on_exit_returns_zero(tmp_project: Path) -> None:
    h = make_app(tmp_project, [Key.DOWN] * 3 + [Key.ENTER])
    assert h.app.run() == 0
    assert h.contexts == []      # no script was run
    assert h.pauses == []


def test_run_first_item_passes_correct_context(tmp_project: Path) -> None:
    # first entry ("Marker" -> marker.py) activated immediately; then exit
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
    assert ctx.menu_path == ()  # an entry at the root level was activated


def test_pause_called_with_message_by_default(tmp_project: Path) -> None:
    # marker.py (first entry) returns 0 -> success; then exit
    keys = [Key.ENTER] + [Key.DOWN, Key.DOWN, Key.DOWN, Key.ENTER]
    h = make_app(tmp_project, keys)
    assert h.app.run() == 0
    assert len(h.pauses) == 1
    assert PRESS_ENTER in h.out.getvalue()


def test_skip_pause_skips_pause_and_message(tmp_project: Path) -> None:
    def runner(ctx):  # the script "asks" to skip the pause
        return RunResult(ok=True, skip_pause=True)

    keys = [Key.ENTER] + [Key.DOWN, Key.DOWN, Key.DOWN, Key.ENTER]
    h = make_app(tmp_project, keys, script_runner=runner)
    assert h.app.run() == 0
    assert h.pauses == []
    assert PRESS_ENTER not in h.out.getvalue()


def test_subfolder_and_back_restores_selection(tmp_project: Path) -> None:
    # root(2)=Tools -> Deep -> Back x2 (with restored selection) -> exit
    keys = [
        Key.DOWN, Key.DOWN, Key.ENTER,   # root: sel 2 (Tools), enter
        Key.ENTER,                        # Tools: enter Deep (sel 0)
        Key.DOWN, Key.DOWN, Key.ENTER,    # Deep has 3 entries -> Back at the end
        Key.DOWN, Key.ENTER,              # Tools: Back (root, restored sel = 2)
        Key.DOWN, Key.ENTER,              # root: Exit
    ]
    h = make_app(tmp_project, keys)
    assert h.app.run() == 0

    headers = [s.splitlines()[0] for s in screens(h)]
    assert "Test menu / Tools" in headers
    deep_idx = headers.index("Test menu / Tools / Deep")
    back_to_root_after_deep = [i for i, x in enumerate(headers) if x == "Test menu" and i > deep_idx]
    assert back_to_root_after_deep, "after Back x2 the root screen appeared"

    # after returning to root the selection must be restored on Tools (index 2)
    first_back_screen = screens(h)[back_to_root_after_deep[0]]
    assert "> Tools" in first_back_screen
    assert "> Marker" not in first_back_screen


def test_exit_to_root_after_script(tmp_project: Path) -> None:
    def runner(ctx):
        return RunResult(ok=True, exit_to_root=True, skip_pause=True)

    # root -> Tools -> Deep -> "To root"; after the script the root screen, then exit
    keys = [
        Key.DOWN, Key.DOWN, Key.ENTER,   # Tools
        Key.ENTER,                        # Deep (selection 0 = To root)
        Key.ENTER,                        # run the script
        Key.DOWN, Key.DOWN, Key.DOWN, Key.ENTER,  # from root: 3x down -> Exit
    ]
    h = make_app(tmp_project, keys, script_runner=runner)
    assert h.app.run() == 0          # if go_root did not work, the keys would run out
    assert len(h.contexts) == 1      # ...and a second ENTER would re-activate the same script
    headers = [s.splitlines()[0] for s in screens(h)]
    deep_idx = headers.index("Test menu / Tools / Deep")
    assert "Test menu" in headers[deep_idx + 1:]


def test_error_result_printed_and_menu_continues(tmp_project: Path) -> None:
    def runner(ctx):
        return RunResult(ok=False, return_code=3, error="RuntimeError: Intentional test error")

    keys = [Key.DOWN, Key.ENTER] + [Key.DOWN, Key.DOWN, Key.ENTER]  # then exit
    h = make_app(tmp_project, keys, script_runner=runner)
    assert h.app.run() == 0
    expected = SCRIPT_ERROR_WITH_CODE.format(error="RuntimeError: Intentional test error", code=3)
    assert expected in h.out.getvalue()
    assert len(h.pauses) == 1  # pause also after a failing script


def test_missing_and_outside_base_scripts_reported(tmp_path: Path) -> None:
    xml = (
        "<?xml version=\"1.0\" encoding=\"utf-8\"?>\n"
        "<menu title=\"T\">\n"
        '  <item name="Missing" dir="scripts" file="missing.py"/>\n'
        '  <item name="Outside" dir="../x" file="y.py"/>\n'
        "</menu>\n"
    )
    (tmp_path / "menu.xml").write_text(xml, encoding="utf-8")
    # Missing(0) -> file-not-found error; Outside(1) -> outside-base error; then Exit.
    # After an error the selection stays on the script entry (menu state does not change).
    keys = [Key.ENTER, Key.DOWN, Key.ENTER, Key.DOWN, Key.ENTER]
    h = make_app(tmp_path, keys)  # the runner should never be called
    assert h.app.run() == 0
    text = h.out.getvalue()
    assert ERR_SCRIPT_OUTSIDE_BASE.partition(":")[0] in text
    assert ERR_SCRIPT_NOT_FOUND.partition(":")[0] in text  # missing file (constant from texts.py)
    assert h.contexts == []


def test_other_key_is_ignored(tmp_project: Path) -> None:
    keys = [Key.OTHER, Key.DOWN, Key.DOWN, Key.DOWN, Key.ENTER]
    h = make_app(tmp_project, keys)
    assert h.app.run() == 0
    assert h.contexts == []  # OTHER did not activate the first entry
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
    assert lines[0] == "Test menu"
    assert "> Marker" in text      # selected first entry
    assert "Error demo" in text    # remaining labels from the XML
    assert "Tools" in text
    assert "Exit" in text          # root's system entry
    assert FOOTER_TEXT in text


def test_clear_and_size_provider_receives_expected_arguments(tmp_project: Path) -> None:
    h = make_app(tmp_project, [Key.DOWN, Key.INTERRUPT])
    h.app.run()
    assert all(stream is h.out for stream in h.clears)
    assert len(h.clears) >= 1        # clearing before every screen
    assert set(h.sizes) == {(80, 24)}
