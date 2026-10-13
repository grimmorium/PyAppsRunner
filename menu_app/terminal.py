"""Obsługa terminala: czyszczenie ekranu, kody ANSI, rozmiar okna (Krok 8).

Wszystkie funkcje działają na strumieniu/parametrach przekazywanych przez
wywołującego - same nie dotykają sys.stdout poza włączeniem trybu ANSI.
"""

from __future__ import annotations

import os
import shutil
from typing import TextIO, Tuple


def enable_ansi() -> None:
    """Włącza przetwarzanie sekwencji ANSI (na Windows przez SetConsoleMode).

    Na POSIX jest to no-op - współczesne terminale obsługują kody ANSI
    domyślnie. Błędy są ignorowane: stdout może być przekierowany i nie
    prowadzić do konsoli, w której tryb ten da się ustawić.
    """
    if os.name != "nt":
        return
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        std_output_handle = -11  # STD_OUTPUT_HANDLE
        mode = ctypes.c_ulong(0)
        handle = kernel32.GetStdHandle(std_output_handle)
        if not kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            return
        enable_virtual_terminal_processing = 0x4
        kernel32.SetConsoleMode(handle, mode.value | enable_virtual_terminal_processing)
    except Exception:  # noqa: BLE001 - przekierowany stdout nie jest konsolą
        pass


def clear_screen(out: TextIO) -> None:
    """Czyści ekran i ustawia kursor w lewym górnym rogu (kody ANSI)."""
    out.write("\x1b[2J\x1b[H")
    out.flush()


def get_size() -> Tuple[int, int]:
    """Rozmiar terminala jako (szerokość, wysokość) z bezpiecznym fallbackiem."""
    size = shutil.get_terminal_size(fallback=(80, 24))
    # os.terminal_size: pola to columns/lines (nie "rows")
    return (size.columns, size.lines)
