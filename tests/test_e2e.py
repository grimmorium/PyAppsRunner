"""End-to-end tests: real App + real run_script (Step 10).

Key sequences are driven through FakeKeyReader on the tmp_project fixture;
pause and screen clearing are no-ops, so a sequence can finish without any
interaction. Additionally one test runs `python main.py` under a pseudoterminal
(pty) - POSIX only (skipif nt).
"""

import io
import os
import select as select_mod
import subprocess
import sys
import time
from pathlib import Path

import pytest

from menu_app.app import App
from menu_app.config import load_menu
from menu_app.keys import Key
from menu_app.testing import FakeKeyReader
from menu_app.texts import SCRIPT_ERROR_WITH_CODE

PROJECT_DIR = Path(__file__).resolve().parents[1]
SCREEN_SEP = "\x00SCR\x00"


def make_e2e(tmp_project: Path, keys):
    """Real App on tmp_project; returns (app, out, pauses)."""
    root = load_menu(tmp_project / "menu.xml")
    out = io.StringIO()
    pauses: list[object] = []

    def clear(stream) -> None:
        stream.write(SCREEN_SEP)  # screen separator for assertions

    app = App(
        root=root,
        base_dir=tmp_project,
        key_reader=FakeKeyReader(keys),
        out=out,
        pause=lambda: pauses.append(None),
        clear=clear,
    )
    return app, out, pauses


def screens(out_text: str) -> list[str]:
    """Individual drawn screens (after the fake-clear separator)."""
    return [p for p in out_text.split(SCREEN_SEP) if p.strip()]


# tmp_project fixture tree:
# root: Marker(0, marker.py), Error demo(1, boom.py), Tools(2), Exit(3)
#   Tools -> Deep -> To root(0, to_root.py), Deep script(1, deep.py)

def test_e2e_marker_script_writes_file(tmp_project: Path) -> None:
    keys = [Key.ENTER] + [Key.DOWN, Key.DOWN, Key.DOWN, Key.ENTER]  # marker; then exit
    app, out, pauses = make_e2e(tmp_project, keys)
    assert app.run() == 0
    marker = tmp_project / "marker.txt"
    assert marker.exists(), "the marker script was not run"
    assert marker.read_text(encoding="utf-8") == "ok"
    assert len(pauses) == 1  # pause after a successful script


def test_e2e_error_script_does_not_kill_app(tmp_project: Path) -> None:
    keys = [Key.DOWN, Key.ENTER] + [Key.DOWN, Key.DOWN, Key.ENTER]  # boom; then exit
    app, out, _pauses = make_e2e(tmp_project, keys)
    assert app.run() == 0  # the menu survived the error and allowed a normal exit
    expected = SCRIPT_ERROR_WITH_CODE.format(error="RuntimeError: Intentional test error", code=1)
    assert expected in out.getvalue()


def test_e2e_exit_to_root_from_deep_level(tmp_project: Path, capsys) -> None:
    keys = [
        Key.DOWN, Key.DOWN, Key.ENTER,   # Tools
        Key.ENTER,                        # Deep (sel 0 = To root)
        Key.ENTER,                        # run to_root.py (exit_to_root)
        Key.DOWN, Key.DOWN, Key.DOWN, Key.ENTER,  # from the main menu: Exit
    ]
    app, out, _pauses = make_e2e(tmp_project, keys)
    assert app.run() == 0
    assert "Returning to main menu" in capsys.readouterr().out
    headers = [s.splitlines()[0] for s in screens(out.getvalue())]
    deep_idx = headers.index("Test menu / Tools / Deep")
    # the first screen after a deep level must be the main menu again
    assert headers[deep_idx + 1] == "Test menu"


def test_e2e_full_path_folder_podfolder_script_back_exit(tmp_project: Path, capsys) -> None:
    keys = [
        Key.DOWN, Key.DOWN, Key.ENTER,   # Tools (root sel = 2)
        Key.ENTER,                        # Deep (sel 0)
        Key.DOWN, Key.ENTER,              # Deep script (sel 1) -> run deep.py
        Key.DOWN, Key.ENTER,              # Back (Deep -> Tools)
        Key.DOWN, Key.ENTER,              # Back (Tools -> root, restored sel = 2)
        Key.DOWN, Key.ENTER,              # Exit
    ]
    app, out, pauses = make_e2e(tmp_project, keys)
    assert app.run() == 0
    assert "Deep script works" in capsys.readouterr().out
    assert len(pauses) == 1


@pytest.mark.skipif(os.name == "nt", reason="pseudoterminal (pty) available only on POSIX")
def test_main_subprocess_under_pty(tmp_project: Path) -> None:
    """`python main.py` under a pseudoterminal: key sequence, code 0 and script text."""
    import pty

    master_fd, slave_fd = pty.openpty()
    proc = subprocess.Popen(
        [
            sys.executable,
            str(PROJECT_DIR / "main.py"),
            "--base-dir", str(tmp_project),
            "--config", str(tmp_project / "menu.xml"),
        ],
        stdin=slave_fd,
        stdout=slave_fd,
        stderr=subprocess.STDOUT,
    )
    os.close(slave_fd)  # the child has its own copy; the parent keeps only the master
    output = bytearray()

    def send_until_quiet(data: bytes, deadline_s: float = 8.0) -> bool:
        """Writes data (if any) and reads until activity stops or EOF."""
        if data:
            os.write(master_fd, data)
        idle = 0.0
        end = time.time() + deadline_s
        while True:
            readable, _, _ = select_mod.select([master_fd], [], [], 0.1)
            if readable:
                try:
                    chunk = os.read(master_fd, 65536)
                except OSError:
                    return False  # pty closed (the child finished)
                if not chunk:
                    return False
                output.extend(chunk)
                idle = 0.0
            else:
                idle += 0.1
                if idle >= 0.4:
                    return True
            if time.time() > end:
                raise AssertionError(
                    f"timeout - the application did not settle; so far: {bytes(output)!r}"
                )

    try:
        send_until_quiet(b"")  # first run + initial screen
        for chunk in (b"zz\r", b"\r", b"z\r", b"\r", b"z\r", b"z\r", b"z\r"):
            # zz\r -> Tools; \r -> Deep; z\r -> deep.py; \r -> pause;
            # z\r, z\r -> Back x2 (root); z\r -> Exit
            send_until_quiet(chunk)
        rc = proc.wait(timeout=10)
    finally:
        if proc.poll() is None:
            proc.kill()
        os.close(master_fd)

    text = bytes(output).decode("utf-8", errors="replace")
    assert rc == 0, f"exit code {rc}; output: {text!r}"
    assert "Deep script works" in text  # the script output reached the terminal
