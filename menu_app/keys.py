"""Key reading on Linux (termios/tty) and Windows (msvcrt) (Step 7).

Imports of platform-specific modules are lazy - inside class methods, so
importing this module works on both systems.
"""

from __future__ import annotations

import os
from enum import Enum
from typing import Protocol, runtime_checkable


class Key(Enum):
    """Normalized key recognized by the main loop."""

    UP = "up"
    DOWN = "down"
    ENTER = "enter"
    INTERRUPT = "interrupt"
    OTHER = "other"


def map_char(ch: str) -> Key:
    """Pure mapping of a single character to a key."""
    if ch in ("a", "A"):
        return Key.UP
    if ch in ("z", "Z"):
        return Key.DOWN
    if ch in ("\r", "\n"):
        return Key.ENTER
    if ch == "\x03":
        return Key.INTERRUPT
    return Key.OTHER


@runtime_checkable
class KeyReader(Protocol):
    """Key reading contract (injected into App)."""

    def read_key(self) -> Key:  # pragma: no cover - protocol
        raise NotImplementedError


class PosixKeyReader:
    """Single-character linear read in cbreak mode; termios always restored."""

    def read_key(self) -> Key:
        import sys
        import termios
        import tty  # lazy - POSIX only

        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setcbreak(fd)
            data = os.read(fd, 1)
            if not data:
                return Key.INTERRUPT  # EOF (e.g. closed stdin)
            ch = data.decode("utf-8", errors="ignore")
            if ch == "\x1b":
                # escape sequence (arrow key e.g. "\\x1b[A") - swallow the rest,
                # so it does not "leak" into subsequent reads
                for _ in range(2):
                    rest = os.read(fd, 1)
                    if not rest:
                        return Key.INTERRUPT
                return Key.OTHER
            return map_char(ch)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


class WindowsKeyReader:
    """Character read via msvcrt.getwch; special keys -> OTHER."""

    def read_key(self) -> Key:
        import msvcrt  # lazy - Windows only

        ch = msvcrt.getwch()
        if ch in ("\x00", "\xe0"):
            # prefix of a special key (arrows etc.) - swallow the extension byte
            msvcrt.getwch()
            return Key.OTHER
        if ch == "\x03":
            return Key.INTERRUPT
        return map_char(ch)


def create_key_reader() -> KeyReader:
    """Chooses the key reader for the current platform (os.name)."""
    if os.name == "nt":
        return WindowsKeyReader()
    return PosixKeyReader()
