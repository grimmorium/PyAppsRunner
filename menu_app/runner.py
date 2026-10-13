"""Ładowanie i uruchamianie skryptów w tym samym procesie (Krok 4).

Skrypt jest ładowany przez importlib pod unikalną nazwą modułu, usuwany
z sys.modules po zakończeniu (każde uruchomienie to świeże wykonanie), a
katalog skryptu na czas wywołania trafia na początek sys.path. Błędy
skryptu nigdy nie propagują się do menu.
"""

from __future__ import annotations

import hashlib
import importlib.util
import sys
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from .script_api import ScriptContext
from .texts import (
    ERR_BAD_RETURN_VALUE,
    ERR_MODULE_PREPARE,
    ERR_NO_RUN_FUNCTION,
    INTERRUPTED_MESSAGE,
    SCRIPT_NONZERO_CODE,
)


@dataclass
class RunResult:
    """Wynik uruchomienia skryptu."""

    ok: bool
    return_code: int = 0  # 0 = sukces
    error: Optional[str] = None  # komunikat dla użytkownika
    exit_to_root: bool = False
    skip_pause: bool = False


def _module_name_for(script_path: Path) -> str:
    digest = hashlib.sha256(str(Path(script_path).resolve()).encode("utf-8")).hexdigest()[:16]
    return f"menu_script_{digest}"


def run_script(ctx: ScriptContext) -> RunResult:
    """Uruchamia ``run(ctx)`` z pliku wskazanego w kontekście.

    Zawsze zwraca RunResult - wyjątki skryptu są łapane i raportowane,
    nigdy nie propagują się dalej (również SystemExit i KeyboardInterrupt).
    """
    module_name = _module_name_for(ctx.script_path)
    script_dir_str = str(ctx.script_dir.resolve())

    def finish(ok: bool, code: int, error: Optional[str]) -> RunResult:
        return RunResult(
            ok=ok,
            return_code=code,
            error=error,
            exit_to_root=ctx.exit_to_root_requested,
            skip_pause=ctx.skip_pause,
        )

    old_path = list(sys.path)
    sys.path.insert(0, script_dir_str)
    try:
        spec_obj = importlib.util.spec_from_file_location(module_name, ctx.script_path)
        if spec_obj is None or spec_obj.loader is None:
            return finish(False, 1, ERR_MODULE_PREPARE.format(path=str(ctx.script_path)))
        module = importlib.util.module_from_spec(spec_obj)
        sys.modules[module_name] = module

        try:
            spec_obj.loader.exec_module(module)
            run_func: Optional[Callable[..., object]] = getattr(module, "run", None)
            if not callable(run_func):
                return finish(False, 1, ERR_NO_RUN_FUNCTION)

            returned = run_func(ctx)
            if returned is None:
                return finish(True, 0, None)
            if isinstance(returned, int) and not isinstance(returned, bool):
                code = int(returned)
                if code == 0:
                    return finish(True, 0, None)
                return finish(False, code, SCRIPT_NONZERO_CODE.format(code=code))
            return finish(False, 1, ERR_BAD_RETURN_VALUE)

        except SystemExit as exc:
            raw = exc.code
            if raw is None:
                code = 0
            elif isinstance(raw, int) and not isinstance(raw, bool):
                code = raw
            else:
                code = 1
            return finish(code == 0, code, None if code == 0 else SCRIPT_NONZERO_CODE.format(code=code))

        except KeyboardInterrupt:
            print(INTERRUPTED_MESSAGE)
            return finish(True, 130, None)

        except Exception as exc:  # noqa: BLE001 - kontrakt: menu zawsze przetrwa błąd skryptu
            traceback.print_exc()
            message = f"{type(exc).__name__}" + (f": {exc}" if str(exc) else "")
            return finish(False, 1, message)

    finally:
        sys.modules.pop(module_name, None)
        sys.path[:] = old_path
