"""Odczyt klawiszy na Linuxie (termios/tty) i Windowsie (msvcrt) (Krok 7).

Importy modułów specyficznych dla platformy są leniwe - wewnątrz metod
klas, dzięki czemu import tego modułu działa na obu systemach.
"""

from __future__ import annotations

import os
from enum import Enum
from typing import Protocol, runtime_checkable


class Key(Enum):
    """Znormalizowany klawisz rozpoznawany przez pętlę główną."""

    UP = "up"
    DOWN = "down"
    ENTER = "enter"
    INTERRUPT = "interrupt"
    OTHER = "other"


def map_char(ch: str) -> Key:
    """Czyste mapowanie pojedynczego znaku na klawisz."""
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
    """Kontrakt odczytu klawisza (wstrzykiwany do App)."""

    def read_key(self) -> Key:  # pragma: no cover - protokół
        raise NotImplementedError


class PosixKeyReader:
    """Liniowy odczyt znaku w trybie cbreak; termios przywracane zawsze."""

    def read_key(self) -> Key:
        import sys
        import termios
        import tty  # leniwe - tylko na POSIX

        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setcbreak(fd)
            data = os.read(fd, 1)
            if not data:
                return Key.INTERRUPT  # EOF (np. zamknięty stdin)
            ch = data.decode("utf-8", errors="ignore")
            if ch == "\x1b":
                # sekwencja ucieczki (strzałka np. "\\x1b[A") - pochłoń resztę,
                # żeby nie "wyciekła" do kolejnych odczytów
                for _ in range(2):
                    rest = os.read(fd, 1)
                    if not rest:
                        return Key.INTERRUPT
                return Key.OTHER
            return map_char(ch)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


class WindowsKeyReader:
    """Odczyt znaku przez msvcrt.getwch; klawisze specjalne -> OTHER."""

    def read_key(self) -> Key:
        import msvcrt  # leniwe - tylko na Windows

        ch = msvcrt.getwch()
        if ch in ("\x00", "\xe0"):
            # przednik klawisza specjalnego (strzałki itd.) - pochłoń rozszerzenie
            msvcrt.getwch()
            return Key.OTHER
        if ch == "\x03":
            return Key.INTERRUPT
        return map_char(ch)


def create_key_reader() -> KeyReader:
    """Wybiera czytnik klawiszy dla bieżącej platformy (os.name)."""
    if os.name == "nt":
        return WindowsKeyReader()
    return PosixKeyReader()
