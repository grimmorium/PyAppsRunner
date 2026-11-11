"""Tests of key reading - character mapping and platform readers (Step 7)."""

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
        # remaining characters -> OTHER (a few "random" ones)
        ("b", Key.OTHER),
        ("5", Key.OTHER),
        (" ", Key.OTHER),
        ("\t", Key.OTHER),
        ("ż", Key.OTHER),  # functional Unicode check - diacritics map to OTHER
    ],
)
def test_map_char(ch: str, expected: Key) -> None:
    assert map_char(ch) is expected


@pytest.mark.skipif(os.name == "nt", reason="POSIX platform test")
def test_create_key_reader_returns_posix_class() -> None:
    assert isinstance(create_key_reader(), PosixKeyReader)


@pytest.mark.skipif(os.name != "nt", reason="Windows platform test")
def test_create_key_reader_returns_windows_class() -> None:
    assert isinstance(create_key_reader(), WindowsKeyReader)


@pytest.mark.skipif(os.name == "nt", reason="pty pseudoterminal available only on POSIX")
def test_posix_key_reader_on_pty() -> None:
    """Reader on a pseudoterminal: keys, escape sequence and termios restoration."""
    import pty
    import termios
    import tty

    master_fd, slave_fd = pty.openpty()
    old_stdin = sys.stdin
    reader = PosixKeyReader()
    try:
        # test baseline state: cbreak (avoids canonical buffering on writes)
        default_attrs = termios.tcgetattr(slave_fd)
        tty.setcbreak(slave_fd)
        cbreak_attrs = termios.tcgetattr(slave_fd)

        sys.stdin = os.fdopen(slave_fd, "rb", closefd=False)

        def read_expected(data: bytes, expected: Key, settle: float = 0.15) -> None:
            pre_state = termios.tcgetattr(slave_fd)
            os.write(master_fd, data)
            time.sleep(settle)
            assert reader.read_key() is expected
            # after read_key() the termios settings must be restored
            assert termios.tcgetattr(slave_fd) == pre_state

        read_expected(b"a", Key.UP)
        read_expected(b"z", Key.DOWN)
        read_expected(b"\r", Key.ENTER)
        # escape sequence (up arrow) -> OTHER, the rest is swallowed
        read_expected(b"\x1b[A", Key.OTHER, settle=0.25)

        # non-trivial restoration check: exit state = canonical
        termios.tcsetattr(slave_fd, termios.TCSADRAIN, default_attrs)
        pre_state = termios.tcgetattr(slave_fd)
        assert pre_state == default_attrs
        os.write(master_fd, b"q\n")  # complete line -> data available after switching to cbreak
        time.sleep(0.25)
        assert reader.read_key() is Key.OTHER  # 'q'
        assert termios.tcgetattr(slave_fd) == default_attrs  # canonical state restored
    finally:
        sys.stdin = old_stdin
        os.close(master_fd)
        os.close(slave_fd)
