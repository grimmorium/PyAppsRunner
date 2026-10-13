"""Testy rozwiązywania ścieżek skryptów (Krok 3 specyfikacji)."""

from pathlib import Path

import pytest

from menu_app.config import ConfigError, ScriptItem
from menu_app.paths import ScriptNotFoundError, resolve_script_path


def _make(base: Path, rel: str) -> Path:
    path = base / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("print('x')\n", encoding="utf-8")
    return path


def test_correct_relative_path(tmp_path: Path) -> None:
    script = _make(tmp_path, "scripts/basic/hello.py")
    item = ScriptItem(name="h", directory="scripts/basic", file="hello.py")
    assert resolve_script_path(tmp_path, item) == script.resolve()


def test_backslash_separator_normalized(tmp_path: Path) -> None:
    script = _make(tmp_path, "scripts/basic/back.py")
    item = ScriptItem(name="b", directory=r"scripts\basic", file="back.py")
    assert resolve_script_path(tmp_path, item) == script.resolve()


def test_absolute_dir_rejected(tmp_path: Path) -> None:
    _make(tmp_path, "a.py")
    for bad_dir in ("/abs/scripts", r"C:\skrypty"):
        item = ScriptItem(name="x", directory=bad_dir, file="a.py")
        with pytest.raises(ConfigError):
            resolve_script_path(tmp_path, item)


def test_escape_outside_base_rejected(tmp_path: Path) -> None:
    # plik istnieje POZA bazą - bez ochrony zostałby znaleziony
    outside = tmp_path / "poza"
    outside.mkdir()
    (outside / "ucieczka.py").write_text("x", encoding="utf-8")
    item = ScriptItem(name="x", directory="../poza", file="ucieczka.py")
    with pytest.raises(ConfigError):
        resolve_script_path(tmp_path, item)


def test_missing_file_raises_not_found(tmp_path: Path) -> None:
    _make(tmp_path, "scripts/basic/other.py")
    item = ScriptItem(name="x", directory="scripts/basic", file="brak.py")
    with pytest.raises(ScriptNotFoundError) as excinfo:
        resolve_script_path(tmp_path, item)
    assert str(excinfo.value)  # komunikat nie jest pusty


def test_directory_instead_of_file_raises_not_found(tmp_path: Path) -> None:
    (tmp_path / "katalog.py").mkdir()
    item = ScriptItem(name="x", directory=".", file="katalog.py")
    with pytest.raises(ScriptNotFoundError):
        resolve_script_path(tmp_path, item)
