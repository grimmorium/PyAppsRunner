"""Rozwiązywanie ścieżek skryptów względem katalogu bazowego (Krok 3).

Sprawdzanie istnienia pliku następuje w momencie uruchomienia, a nie przy
wczytywaniu XML - menu działa mimo brakującego skryptu.
"""

from __future__ import annotations

import re
from pathlib import Path

from .config import ConfigError, ScriptItem
from .texts import ERR_ABSOLUTE_DIR, ERR_SCRIPT_NOT_FOUND, ERR_SCRIPT_OUTSIDE_BASE


class ScriptNotFoundError(Exception):
    """Brak pliku skryptu w momencie uruchamiania (komunikat zawiera ścieżkę)."""


_DRIVE_LETTER_RE = re.compile(r"^[A-Za-z]:")


def resolve_script_path(base_dir: Path, item: ScriptItem) -> Path:
    """Zwraca rozwiązaną absolutną ścieżkę do pliku skryptu.

    Reguły: separator "\" w ``dir`` zamieniany na "/", katalog musi być
    relatywny, wynik musi leżeć wewnątrz base_dir (ochrona przed "../../").
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
