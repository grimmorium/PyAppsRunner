"""Resolving script paths relative to the base directory (Step 3).

File existence is checked at run time, not when reading the XML - the menu
works even if a script is missing.
"""

from __future__ import annotations

import re
from pathlib import Path

from .config import ConfigError, ScriptItem
from .texts import ERR_ABSOLUTE_DIR, ERR_SCRIPT_NOT_FOUND, ERR_SCRIPT_OUTSIDE_BASE


class ScriptNotFoundError(Exception):
    """Script file missing at launch time (message includes the path)."""


_DRIVE_LETTER_RE = re.compile(r"^[A-Za-z]:")


def resolve_script_path(base_dir: Path, item: ScriptItem) -> Path:
    """Returns the resolved absolute path to the script file.

    Rules: the "\\" separator in ``dir`` is replaced with "/", the directory
    must be relative, and the result must lie inside base_dir (protection
    against "../../").
    """
    base = Path(base_dir).resolve()
    directory = item.directory.replace("\\", "/")
    if directory.startswith("/") or _DRIVE_LETTER_RE.match(directory):
        raise ConfigError(ERR_ABSOLUTE_DIR.format(dir=item.directory))

    candidate = (base / directory / item.file).resolve()
    if not candidate.is_relative_to(base):
        raise ConfigError(ERR_SCRIPT_OUTSIDE_BASE.format(path=str(candidate)))

    if not candidate.exists() or not candidate.is_file():
        raise ScriptNotFoundError(ERR_SCRIPT_NOT_FOUND.format(path=str(candidate)))
    return candidate
