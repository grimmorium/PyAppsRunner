"""Testy end-to-end: prawdziwy App + prawdziwy run_script (Krok 10).

Sekwencje klawiszy odpalane są przez FakeKeyReader na fixture tmp_project;
pauza i czyszczenie ekranu to no-op, więc sekwencja może się zakończyć bez
interakcji. Dodatkowo jeden test uruchamia `python main.py` pod pseudoterminalem
(pty) - tylko POSIX (skipif nt).
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
    """Prawdziwy App na tmp_project; zwraca (app, out, pauses)."""
    root = load_menu(tmp_project / "menu.xml")
    out = io.StringIO()
    pauses: list[object] = []

    def clear(stream) -> None:
        stream.write(SCREEN_SEP)  # separator ekranów do assertions

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
    """Poszczególne narysowane ekrany (po separatorze z fake'owego clear)."""
    return [p for p in out_text.split(SCREEN_SEP) if p.strip()]


# Drzewo fixture tmp_project:
# root: Znacznik(0, marker.py), Błęd demo(1, boom.py), Narzędzia(2), Wyjście(3)
#   Narzędzia -> Głęboko -> Do roota(0, to_root.py), Głęboki skrypt(1, deep.py)

def test_e2e_marker_script_writes_file(tmp_project: Path) -> None:
    keys = [Key.ENTER] + [Key.DOWN, Key.DOWN, Key.DOWN, Key.ENTER]  # marker; potem wyjście
    app, out, pauses = make_e2e(tmp_project, keys)
    assert app.run() == 0
    marker = tmp_project / "marker.txt"
    assert marker.exists(), "skrypt-znacznik nie został uruchomiony"
    assert marker.read_text(encoding="utf-8") == "ok"
    assert len(pauses) == 1  # pauza po pomyślnym skrypcie


def test_e2e_error_script_does_not_kill_app(tmp_project: Path) -> None:
    keys = [Key.DOWN, Key.ENTER] + [Key.DOWN, Key.DOWN, Key.ENTER]  # boom; potem wyjście
    app, out, _pauses = make_e2e(tmp_project, keys)
    assert app.run() == 0  # menu przeżyło błąd i pozwoliło normalnie wyjść
    expected = SCRIPT_ERROR_WITH_CODE.format(error="RuntimeError: Celowy błąd testowy", code=1)
    assert expected in out.getvalue()


def test_e2e_exit_to_root_from_deep_level(tmp_project: Path, capsys) -> None:
    keys = [
        Key.DOWN, Key.DOWN, Key.ENTER,   # Narzędzia
        Key.ENTER,                        # Głęboko (sel 0 = Do roota)
        Key.ENTER,                        # uruchomienie to_root.py (exit_to_root)
        Key.DOWN, Key.DOWN, Key.DOWN, Key.ENTER,  # z menu głównego: Wyjście
    ]
    app, out, _pauses = make_e2e(tmp_project, keys)
    assert app.run() == 0
    assert "Zwracam do menu glownego" in capsys.readouterr().out
    headers = [s.splitlines()[0] for s in screens(out.getvalue())]
    deep_idx = headers.index("Menu testowe / Narzędzia / Głęboko")
    # pierwszy ekran po głębokim poziomie musi być znowu menu głównym
    assert headers[deep_idx + 1] == "Menu testowe"


def test_e2e_full_path_folder_podfolder_script_back_exit(tmp_project: Path, capsys) -> None:
    keys = [
        Key.DOWN, Key.DOWN, Key.ENTER,   # Narzędzia (sel root = 2)
        Key.ENTER,                        # Głęboko (sel 0)
        Key.DOWN, Key.ENTER,              # Głęboki skrypt (sel 1) -> uruchomienie deep.py
        Key.DOWN, Key.ENTER,              # Wstecz (Głęboko -> Narzędzia)
        Key.DOWN, Key.ENTER,              # Wstecz (Narzędzia -> root, sel przywrócone = 2)
        Key.DOWN, Key.ENTER,              # Wyjście
    ]
    app, out, pauses = make_e2e(tmp_project, keys)
    assert app.run() == 0
    assert "Gleboki skrypt dziala" in capsys.readouterr().out
    assert len(pauses) == 1


@pytest.mark.skipif(os.name == "nt", reason="pseudoterminal (pty) dostępny tylko na POSIX")
def test_main_subprocess_under_pty(tmp_project: Path) -> None:
    """`python main.py` pod pseudoterminalem: sekwencja klawiszy, kod 0 i tekst skryptu."""
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
    os.close(slave_fd)  # dziecko ma własną kopię; rodzic trzyma tylko master
    output = bytearray()

    def send_until_quiet(data: bytes, deadline_s: float = 8.0) -> bool:
        """Zapisuje dane (jeśli są) i czyta do ustania aktywności lub EOF."""
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
                    return False  # pty zamknięte (dziecko zakończyło pracę)
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
                    f"timeout - aplikacja nie ustabilizowała się; dotąd: {bytes(output)!r}"
                )

    try:
        send_until_quiet(b"")  # pierwsze uruchomienie + ekran początkowy
        for chunk in (b"zz\r", b"\r", b"z\r", b"\r", b"z\r", b"z\r", b"z\r"):
            # zz\r -> Narzędzia; \r -> Głęboko; z\r -> deep.py; \r -> pauza;
            # z\r, z\r -> Wstecz x2 (root); z\r -> Wyjście
            send_until_quiet(chunk)
        rc = proc.wait(timeout=10)
    finally:
        if proc.poll() is None:
            proc.kill()
        os.close(master_fd)

    text = bytes(output).decode("utf-8", errors="replace")
    assert rc == 0, f"kod wyjścia {rc}; wynik: {text!r}"
    assert "Gleboki skrypt dziala" in text  # wydruk skryptu dotarł do terminala
