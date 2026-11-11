"""Terminal handling: screen clearing, ANSI codes, window size (Step 8).

All functions operate on the stream/parameters passed by the caller - they
do not touch sys.stdout themselves except for enabling ANSI mode.
"""

from __future__ import annotations

import os
import shutil
from typing import TextIO, Tuple


def enable_ansi() -> None:
    """Enables processing of ANSI sequences (on Windows via SetConsoleMode).

    On POSIX this is a no-op - modern terminals support ANSI codes by
    default. Errors are ignored: stdout may be redirected and not lead to
    a console where the mode can be set.
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
    except Exception:  # noqa: BLE001 - redirected stdout is not a console
        pass


def clear_screen(out: TextIO) -> None:
    """Clears the screen and moves the cursor to the top-left corner (ANSI codes)."""
    out.write("\x1b[2J\x1b[H")
    out.flush()


def get_size() -> Tuple[int, int]:
    """Terminal size as (width, height) with a safe fallback."""
    size = shutil.get_terminal_size(fallback=(80, 24))
    # os.terminal_size: fields are columns/lines (not "rows")
    return (size.columns, size.lines)
