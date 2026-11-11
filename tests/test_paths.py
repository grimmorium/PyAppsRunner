"""Tests of script path resolution (Step 3 of the specification)."""

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
    for bad_dir in ("/abs/scripts", r"C:\scripts"):
        item = ScriptItem(name="x", directory=bad_dir, file="a.py")
        with pytest.raises(ConfigError):
            resolve_script_path(tmp_path, item)


def test_escape_outside_base_rejected(tmp_path: Path) -> None:
    # the file exists OUTSIDE the base - without protection it would be found
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "escape.py").write_text("x", encoding="utf-8")
    item = ScriptItem(name="x", directory="../outside", file="escape.py")
    with pytest.raises(ConfigError):
        resolve_script_path(tmp_path, item)


def test_missing_file_raises_not_found(tmp_path: Path) -> None:
    _make(tmp_path, "scripts/basic/other.py")
    item = ScriptItem(name="x", directory="scripts/basic", file="missing.py")
    with pytest.raises(ScriptNotFoundError) as excinfo:
        resolve_script_path(tmp_path, item)
    assert str(excinfo.value)  # message is not empty


def test_directory_instead_of_file_raises_not_found(tmp_path: Path) -> None:
    (tmp_path / "catalog.py").mkdir()
    item = ScriptItem(name="x", directory=".", file="catalog.py")
    with pytest.raises(ScriptNotFoundError):
        resolve_script_path(tmp_path, item)
