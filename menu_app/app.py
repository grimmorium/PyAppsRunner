"""Pętla główna aplikacji łącząca nawigację, renderer i runner (Krok 8).

Logika jest odseparowana od I/O: czytnik klawiszy, strumień wyjścia,
uruchamianie skryptów oraz pauza są wstrzykiwane w konstruktorze. Błędy
ścieżek i błędy uruchomienia nigdy nie przerywają pętli menu.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, List, TextIO, Tuple

from .config import ConfigError, Folder
from .keys import Key, KeyReader
from .navigator import Navigator, Quit, RunScript
from .paths import ScriptNotFoundError, resolve_script_path
from .renderer import render_screen
from .runner import RunResult, run_script
from .script_api import ScriptContext
from .terminal import clear_screen, get_size
from .texts import PRESS_ENTER, SCRIPT_ERROR_WITH_CODE


class App:
    """Pętla główna: rysuje ekran -> czyta klawisz -> wykonuje akcję."""

    def __init__(
        self,
        root: Folder,
        base_dir: Path,
        key_reader: KeyReader,
        out: TextIO,
        script_runner: Callable[[ScriptContext], RunResult] = run_script,
        pause: Callable[[], None] = input,
        size_provider: Callable[[], Tuple[int, int]] = get_size,
        clear: Callable[[TextIO], None] = clear_screen,
    ) -> None:
        self._nav = Navigator(root)
        self._base_dir = base_dir
        self._key_reader = key_reader
        self._out = out
        self._script_runner = script_runner
        self._pause_fn = pause
        self._size_provider = size_provider
        self._clear = clear

    def run(self) -> int:
        """Uruchamia pętlę główną; zwraca kod wyjścia (0 = normalne zakończenie)."""
        while True:
            self._draw()
            key = self._key_reader.read_key()
            if key is Key.UP:
                self._nav.move_up()
            elif key is Key.DOWN:
                self._nav.move_down()
            elif key is Key.INTERRUPT:
                return 0
            elif key is Key.OTHER:
                continue
            else:  # Key.ENTER
                action = self._nav.activate()
                if isinstance(action, Quit):
                    return 0
                if isinstance(action, RunScript):
                    self._run_script_action(action)

    def _draw(self) -> None:
        """Czyści ekran i wypisuje bieżący widok menu."""
        width, height = self._size_provider()
        labels: List[str] = [entry.label for entry in self._nav.entries()]
        screen = render_screen(
            title=self._nav.title(),
            breadcrumb=self._nav.breadcrumb(),
            labels=labels,
            selected=self._nav.selected_index(),
            width=width,
            height=height,
        )
        self._clear(self._out)
        self._out.write(screen)
        self._out.flush()

    def _wait_for_enter(self) -> None:
        """Pauza po skrypcie/błędzie; EOF i Ctrl+C kończą tylko pauzę."""
        print(PRESS_ENTER, file=self._out)
        try:
            self._pause_fn()
        except (EOFError, KeyboardInterrupt):
            pass

    def _run_script_action(self, action: RunScript) -> None:
        """Rozwiązuje ścieżkę, uruchamia skrypt i raportuje wynik w menu."""
        try:
            script_path = resolve_script_path(self._base_dir, action.item)
        except (ConfigError, ScriptNotFoundError) as exc:
            print(str(exc), file=self._out)
            self._wait_for_enter()
            return

        ctx = ScriptContext(
            base_dir=self._base_dir,
            script_path=script_path,
            script_dir=script_path.parent,
            menu_path=action.menu_path,
        )
        result = self._script_runner(ctx)
        if not result.ok:
            print(
                SCRIPT_ERROR_WITH_CODE.format(error=result.error, code=result.return_code),
                file=self._out,
            )
        if result.exit_to_root:
            self._nav.go_root()
        if not result.skip_pause:
            self._wait_for_enter()
