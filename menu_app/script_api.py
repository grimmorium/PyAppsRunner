"""Contract of a script invoked by the menu (Step 4 of the specification).

A script is an ordinary .py file with a module-level ``run(ctx)`` function:
a return value of None/0 means success, any other integer - an error. The
return to the menu happens via simply finishing run(). A script does not
change the process working directory; its directory is available on sys.path.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Tuple

from .texts import PRESS_ENTER


@dataclass
class ScriptContext:
    """Context passed to the ``run(ctx)`` function of an invoked script."""

    base_dir: Path  # application base directory
    script_path: Path  # full path of the file being run
    script_dir: Path  # directory containing the script
    menu_path: Tuple[str, ...] = ()  # e.g. ("Tools", "Advanced")
    skip_pause: bool = False  # True -> no "Press Enter..." pause
    exit_to_root_requested: bool = field(default=False)

    def exit_to_root(self) -> None:
        """Requests returning to the main menu after run() finishes."""
        self.exit_to_root_requested = True

    def pause(self, message: str = PRESS_ENTER) -> None:
        """Pause for the user (input); EOFError is ignored."""
        try:
            input(message)
        except EOFError:
            pass
