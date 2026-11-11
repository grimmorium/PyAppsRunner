"""Loading and running scripts in the same process (Step 4).

A script is loaded via importlib under a unique module name, removed from
sys.modules after finishing (every run is a fresh execution), and its
directory is placed at the front of sys.path for the duration of the call.
Script errors never propagate to the menu.
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
    """Script run result."""

    ok: bool
    return_code: int = 0  # 0 = success
    error: Optional[str] = None  # message for the user
    exit_to_root: bool = False
    skip_pause: bool = False


def _module_name_for(script_path: Path) -> str:
    digest = hashlib.sha256(str(Path(script_path).resolve()).encode("utf-8")).hexdigest()[:16]
    return f"menu_script_{digest}"


def run_script(ctx: ScriptContext) -> RunResult:
    """Runs ``run(ctx)`` from the file indicated in the context.

    Always returns a RunResult - script exceptions are caught and reported,
    never propagated further (including SystemExit and KeyboardInterrupt).
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

        except Exception as exc:  # noqa: BLE001 - contract: the menu always survives a script error
            traceback.print_exc()
            message = f"{type(exc).__name__}" + (f": {exc}" if str(exc) else "")
            return finish(False, 1, message)

    finally:
        sys.modules.pop(module_name, None)
        sys.path[:] = old_path
