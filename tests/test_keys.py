"""Testy odczytu klawiszy - mapowanie znaków i czytniki platformowe (Krok 7)."""

import os
import sys
import time

import pytest

from menu_app.keys import Key, PosixKeyReader, WindowsKeyReader, create_key_reader, map_char


@pytest.mark.parametrize(
    ("ch", "expected"),
    [
        ("a", Key.UP),
        ("A", Key.UP),
        ("z", Key.DOWN),
        ("Z", Key.DOWN),
        ("\r", Key.ENTER),
        ("\n", Key.ENTER),
        ("\x03", Key.INTERRUPT),
        # pozostałe znaki -> OTHER (kilka "losowych")
        ("b", Key.OTHER),
        ("5", Key.OTHER),
        (" ", Key.OTHER),
        ("\t", Key.OTHER),
        ("ż", Key.OTHER),
    ],
)
def test_map_char(ch: str, expected: Key) -> None:
    assert map_char(ch) is expected


@pytest.mark.skipif(os.name == "nt", reason="test platformy POSIX")
def test_create_key_reader_returns_posix_class() -> None:
    assert isinstance(create_key_reader(), PosixKeyReader)


@pytest.mark.skipif(os.name != "nt", reason="test platformy Windows")
def test_create_key_reader_returns_windows_class() -> None:
    assert isinstance(create_key_reader(), WindowsKeyReader)


@pytest.mark.skipif(os.name == "nt", reason="pseudoterminal pty dostępny tylko na POSIX")
def test_posix_key_reader_on_pty() -> None:
    """Czytnik na pseudoterminalu: klawisze, sekwencja ucieczki i przywracanie termios."""
    import pty
    import termios
    import tty

    master_fd, slave_fd = pty.openpty()
    old_stdin = sys.stdin
    reader = PosixKeyReader()
    try:
        # stan bazowy testu: cbreak (unikamy buforowania kanonicznego przy zapisach)
        default_attrs = termios.tcgetattr(slave_fd)
        tty.setcbreak(slave_fd)
        cbreak_attrs = termios.tcgetattr(slave_fd)

        sys.stdin = os.fdopen(slave_fd, "rb", closefd=False)

        def read_expected(data: bytes, expected: Key, settle: float = 0.15) -> None:
            pre_state = termios.tcgetattr(slave_fd)
            os.write(master_fd, data)
            time.sleep(settle)
            assert reader.read_key() is expected
            # po read_key() ustawienia termios muszą być przywrócone
            assert termios.tcgetattr(slave_fd) == pre_state

        read_expected(b"a", Key.UP)
        read_expected(b"z", Key.DOWN)
        read_expected(b"\r", Key.ENTER)
        # sekwencja ucieczki (strzałka w górę) -> OTHER, reszta pochłonięta
        read_expected(b"\x1b[A", Key.OTHER, settle=0.25)

        # niebanalne sprawdzenie przywracania: stan wyjściowy = kanoniczny
        termios.tcsetattr(slave_fd, termios.TCSADRAIN, default_attrs)
        pre_state = termios.tcgetattr(slave_fd)
        assert pre_state == default_attrs
        os.write(master_fd, b"q\n")  # linia kompletna -> dane dostępne po przełączeniu na cbreak
        time.sleep(0.25)
        assert reader.read_key() is Key.OTHER  # 'q'
        assert termios.tcgetattr(slave_fd) == default_attrs  # przywrócony stan kanoniczny
    finally:
        sys.stdin = old_stdin
        os.close(master_fd)
        os.close(slave_fd)
