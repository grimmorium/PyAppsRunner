"""Tests of the main() entry point - argv, exit codes and error messages (Step 9).

The configuration is loaded from a temporary file; the key reader is injected
as a parameter, so the tests do not require a real terminal.
"""

import io
from pathlib import Path

from main import main
from menu_app.keys import Key
from menu_app.testing import FakeKeyReader

VALID_EMPTY_MENU = '<?xml version="1.0" encoding="utf-8"?><menu/>'


def _write_config(tmp_path: Path, content: str) -> Path:
    xml_file = tmp_path / "menu.xml"
    xml_file.write_text(content, encoding="utf-8")
    return xml_file


def test_invalid_xml_returns_2_with_message(tmp_path: Path, capsys) -> None:
    cfg = _write_config(tmp_path, "<menu><folder name='x'></menu>")  # unbalanced tags
    rc = main(["--config", str(cfg), "--base-dir", str(tmp_path)])
    err = capsys.readouterr().err
    assert rc == 2
    assert "Configuration error" in err


def test_missing_config_returns_2_with_message(tmp_path: Path, capsys) -> None:
    missing = tmp_path / "missing.xml"
    rc = main(["--config", str(missing), "--base-dir", str(tmp_path)])
    err = capsys.readouterr().err
    assert rc == 2
    assert "Configuration file does not exist" in err


def test_default_config_path_is_base_dir_menu_xml(tmp_path: Path, capsys) -> None:
    # without --config we read <base-dir>/menu.xml (missing here -> code 2)
    rc = main(["--base-dir", str(tmp_path)])
    err = capsys.readouterr().err
    assert rc == 2
    assert "Configuration file does not exist" in err


def test_no_tty_without_injected_reader_returns_3(tmp_path: Path, capsys) -> None:
    cfg = _write_config(tmp_path, VALID_EMPTY_MENU)  # valid configuration -> we reach the TTY check
    rc = main(["--config", str(cfg), "--base-dir", str(tmp_path)])
    err = capsys.readouterr().err
    assert rc == 3
    assert "stdin is not a terminal" in err


def test_injected_reader_runs_empty_menu_to_exit_zero(tmp_path: Path) -> None:
    cfg = _write_config(tmp_path, VALID_EMPTY_MENU)
    out = io.StringIO()
    # an empty menu = a single system entry "Exit" (selected from the start)
    rc = main(
        ["--config", str(cfg), "--base-dir", str(tmp_path)],
        key_reader=FakeKeyReader([Key.ENTER]),
        out=out,
    )
    assert rc == 0
    assert "Exit" in out.getvalue()
