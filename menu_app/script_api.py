"""Kontrakt skryptu wywoływanego przez menu (Krok 4 specyfikacji).

Skrypt to zwykły plik .py z funkcją ``run(ctx)`` na poziomie modułu:
wartość None/0 oznacza sukces, inna liczba całkowita - błąd. Powrót do
menu następuje przez zwykłe zakończenie run(). Skrypt nie zmienia
katalogu roboczego procesu; katalog skryptu jest dostępny w sys.path.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Tuple

from .texts import PRESS_ENTER


@dataclass
class ScriptContext:
    """Kontekst przekazywany funkcji ``run(ctx)`` wywoływanego skryptu."""

    base_dir: Path  # katalog bazowy aplikacji
    script_path: Path  # pełna ścieżka uruchamianego pliku
    script_dir: Path  # katalog, w którym leży skrypt
    menu_path: Tuple[str, ...] = ()  # np. ("Narzędzia", "Zaawansowane")
    skip_pause: bool = False  # True -> brak pauzy "Naciśnij Enter..."
    exit_to_root_requested: bool = field(default=False)

    def exit_to_root(self) -> None:
        """Wymaga powrotu do menu głównego po zakończeniu run()."""
        self.exit_to_root_requested = True

    def pause(self, message: str = PRESS_ENTER) -> None:
        """Pauza dla użytkownika (input); EOFError jest ignorowane."""
        try:
            input(message)
        except EOFError:
            pass
