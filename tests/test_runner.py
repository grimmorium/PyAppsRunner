"""Testy kontraktu skryptu i runnera (Krok 4 specyfikacji)."""

import sys
from pathlib import Path

import pytest

from menu_app.runner import RunResult, run_script
from menu_app.script_api import ScriptContext
from menu_app.texts import ERR_NO_RUN_FUNCTION


def make_ctx(tmp_path: Path, source: str, name: str = "script.py") -> ScriptContext:
    path = tmp_path / name
    path.write_text(source, encoding="utf-8")
    return ScriptContext(
        base_dir=tmp_path,
        script_path=path,
        script_dir=path.parent,
        menu_path=("Test",),
    )


def run(tmp_path: Path, source: str) -> RunResult:
    return run_script(make_ctx(tmp_path, source))


def test_run_returns_none_is_ok(tmp_path: Path) -> None:
    result = run(tmp_path, "def run(ctx):\n    return None\n")
    assert result.ok is True
    assert result.return_code == 0
    assert result.error is None


def test_run_returns_zero_is_ok(tmp_path: Path) -> None:
    result = run(tmp_path, "def run(ctx):\n    return 0\n")
    assert result.ok is True
    assert result.return_code == 0


def test_run_returns_nonzero_is_error(tmp_path: Path) -> None:
    result = run(tmp_path, "def run(ctx):\n    return 3\n")
    assert result.ok is False
    assert result.return_code == 3
    assert result.error is not None


def test_missing_run_function(tmp_path: Path) -> None:
    result = run(tmp_path, "WARTOSCIOWANIE_MODULU = 1\n")
    assert result.ok is False
    assert result.error == ERR_NO_RUN_FUNCTION


@pytest.mark.parametrize("bad_run", ['run = "to nie funkcja"', "run = 42"])
def test_run_not_callable(tmp_path: Path, bad_run: str) -> None:
    result = run(tmp_path, f"{bad_run}\n")
    assert result.ok is False
    assert result.error == ERR_NO_RUN_FUNCTION


def test_exception_in_run_does_not_kill_menu(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    source = "def run(ctx):\n    raise RuntimeError('coś poszło nie tak')\n"
    result = run(tmp_path, source)  # nie może rzucić wyjątku
    assert result.ok is False
    assert result.return_code == 1
    assert "RuntimeError" in (result.error or "")
    err = capsys.readouterr().err
    assert "Traceback" in err


def test_import_time_syntax_error(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    result = run(tmp_path, "def run(:\n    pass\n")
    assert result.ok is False
    assert result.error is not None
    assert "Traceback" in capsys.readouterr().err


def test_import_time_module_level_error(tmp_path: Path) -> None:
    source = 'import nieistniejacy_modul_xyz123\n\ndef run(ctx):\n    return 0\n'
    result = run(tmp_path, source)
    assert result.ok is False
    assert "ModuleNotFoundError" in (result.error or "")


@pytest.mark.parametrize(
    ("source", "expected_code"),
    [
        ("import sys\n\ndef run(ctx):\n    sys.exit(0)\n", 0),
        ("import sys\n\ndef run(ctx):\n    sys.exit(5)\n", 5),
        ('import sys\n\ndef run(ctx):\n    sys.exit("tekst")\n', 1),
    ],
)
def test_system_exit_variants(tmp_path: Path, source: str, expected_code: int) -> None:
    result = run(tmp_path, source)
    assert result.return_code == expected_code
    assert (result.ok is True) == (expected_code == 0)


def test_keyboard_interrupt_in_run_is_not_error(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    result = run(tmp_path, "def run(ctx):\n    raise KeyboardInterrupt\n")
    assert result.ok is True
    assert result.error is None
    assert "Przerwano" in capsys.readouterr().out


def test_exit_to_root_flag_copied(tmp_path: Path) -> None:
    source = "def run(ctx):\n    ctx.exit_to_root()\n    return None\n"
    result = run(tmp_path, source)
    assert result.ok is True
    assert result.exit_to_root is True


def test_skip_pause_flag_copied(tmp_path: Path) -> None:
    source = "def run(ctx):\n    ctx.skip_pause = True\n    return 0\n"
    result = run(tmp_path, source)
    assert result.ok is True
    assert result.skip_pause is True


@pytest.mark.parametrize("source", ["def run(ctx):\n    return 0\n",
                                    "def run(ctx):\n    raise ValueError('x')\n"])
def test_sys_path_restored_after_run(tmp_path: Path, source: str) -> None:
    before = list(sys.path)
    try:
        run_script(make_ctx(tmp_path, source))
    finally:
        assert sys.path == before


def test_no_menu_module_left_in_sys_modules(tmp_path: Path) -> None:
    result = run(tmp_path, "def run(ctx):\n    return 0\n")
    assert result.ok is True
    leftovers = [name for name in sys.modules if name.startswith("menu_script_")]
    assert leftovers == []


def test_script_dir_first_on_sys_path_during_run(tmp_path: Path) -> None:
    source = (
        "def run(ctx):\n"
        "    import sys\n"
        "    first = str(sys.path[0]).lower()\n"
        '    target = str(ctx.script_dir.resolve()).lower()\n'
        "    return 0 if first == target else 7\n"
    )
    result = run(tmp_path, source)
    assert result.ok is True
    assert result.return_code == 0


def test_sibling_module_import_works(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    (tmp_path / "helper_mod.py").write_text('WARTOSC = "pomocnik-dziala"\n', encoding="utf-8")
    source = "import helper_mod\n\ndef run(ctx):\n    print(helper_mod.WARTOSC)\n    return 0\n"
    result = run(tmp_path, source)
    assert result.ok is True
    assert "pomocnik-dziala" in capsys.readouterr().out


def test_two_runs_execute_fresh_module_state(tmp_path: Path) -> None:
    # zmienna modułu nie może zostać zachowana między uruchomieniami
    source = (
        "RUNS = 0\n"
        "\n"
        "def run(ctx):\n"
        "    global RUNS\n"
        "    RUNS += 1\n"
        '    (ctx.base_dir / "runs.txt").write_text(str(RUNS), encoding="utf-8")\n'
        "    return 0\n"
    )
    ctx = make_ctx(tmp_path, source)
    assert run_script(ctx).ok is True
    assert run_script(ctx).ok is True
    assert (tmp_path / "runs.txt").read_text(encoding="utf-8") == "1"


def test_script_stdout_visible(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    source = 'def run(ctx):\n    print("Hello ze skryptu")\n    return 0\n'
    result = run(tmp_path, source)
    assert result.ok is True
    out = capsys.readouterr().out
    assert "Hello ze skryptu" in out
