"""Testy punktu wejścia main() - argv, kody wyjścia i komunikaty błędów (Krok 9).

Konfiguracja ładowana jest z pliku tymczasowego; czytnik klawiszy wstrzykiwany
jest parametrem, więc testy nie wymagają prawdziwego terminala.
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
    cfg = _write_config(tmp_path, "<menu><folder name='x'></menu>")  # niezbalansowane tagi
    rc = main(["--config", str(cfg), "--base-dir", str(tmp_path)])
    err = capsys.readouterr().err
    assert rc == 2
    assert "Błąd konfiguracji" in err


def test_missing_config_returns_2_with_message(tmp_path: Path, capsys) -> None:
    missing = tmp_path / "brak.xml"
    rc = main(["--config", str(missing), "--base-dir", str(tmp_path)])
    err = capsys.readouterr().err
    assert rc == 2
    assert "Plik konfiguracyjny nie istnieje" in err


def test_default_config_path_is_base_dir_menu_xml(tmp_path: Path, capsys) -> None:
    # bez --config odczytujemy <base-dir>/menu.xml (tu go brak -> kod 2)
    rc = main(["--base-dir", str(tmp_path)])
    err = capsys.readouterr().err
    assert rc == 2
    assert "Plik konfiguracyjny nie istnieje" in err


def test_no_tty_without_injected_reader_returns_3(tmp_path: Path, capsys) -> None:
    cfg = _write_config(tmp_path, VALID_EMPTY_MENU)  # poprawna konfiguracja -> docieramy do checku TTY
    rc = main(["--config", str(cfg), "--base-dir", str(tmp_path)])
    err = capsys.readouterr().err
    assert rc == 3
    assert "stdin nie jest terminalem" in err


def test_injected_reader_runs_empty_menu_to_exit_zero(tmp_path: Path) -> None:
    cfg = _write_config(tmp_path, VALID_EMPTY_MENU)
    out = io.StringIO()
    # puste menu = pojedyncza pozycja systemowa "Wyjście" (zaznaczona od początku)
    rc = main(
        ["--config", str(cfg), "--base-dir", str(tmp_path)],
        key_reader=FakeKeyReader([Key.ENTER]),
        out=out,
    )
    assert rc == 0
    assert "Wyjście" in out.getvalue()
