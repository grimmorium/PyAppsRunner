"""Stan nawigacji po menu - czysta logika bez I/O (Krok 5 specyfikacji).

Nawigacja jest cykliczna; na końcu każdej listy stoi pozycja systemowa
(EXIT w root, BACK w podmenu). Powrót z podmenu przywraca zaznaczenie
zapisane przed wejściem.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Tuple, Union

from .config import Folder, MenuNode, ScriptItem
from .texts import BACK_LABEL, EXIT_LABEL


class EntryKind(Enum):
    """Rodzaj pozycji menu."""

    FOLDER = "folder"
    SCRIPT = "script"
    BACK = "back"
    EXIT = "exit"


@dataclass(frozen=True)
class Entry:
    """Pozycja listy menu (dzieci folderu + pozycja systemowa)."""

    kind: EntryKind
    label: str
    node: Optional[MenuNode]  # Folder lub ScriptItem; None dla BACK/EXIT


@dataclass(frozen=True)
class Stay:
    """Nic się nie dzieje - pętla rysuje kolejny ekran."""


@dataclass(frozen=True)
class RunScript:
    """Uruchom skrypt z pozycji wskazanej w menu_path."""

    item: ScriptItem
    menu_path: Tuple[str, ...]


@dataclass(frozen=True)
class Quit:
    """Zakończ program (kod wyjścia 0)."""


NavigatorAction = Union[Stay, RunScript, Quit]


class Navigator:
    """Stan nawigacji: stos folderów + zaznaczenie per poziom."""

    def __init__(self, root: Folder) -> None:
        self._root = root
        # (folder, indeks zaznaczenia); wierzchołek stosu = bieżący poziom
        self._stack: List[Tuple[Folder, int]] = [(root, 0)]

    def _current(self) -> Tuple[Folder, int]:
        return self._stack[-1]

    def entries(self) -> list[Entry]:
        """Dzieci bieżącego folderu + pozycja systemowa na końcu."""
        folder, _ = self._current()
        result: List[Entry] = []
        for node in folder.children:
            if isinstance(node, Folder):
                result.append(Entry(kind=EntryKind.FOLDER, label=node.name, node=node))
            else:
                result.append(Entry(kind=EntryKind.SCRIPT, label=node.name, node=node))
        is_root = len(self._stack) == 1
        if is_root:
            result.append(Entry(kind=EntryKind.EXIT, label=EXIT_LABEL, node=None))
        else:
            result.append(Entry(kind=EntryKind.BACK, label=BACK_LABEL, node=None))
        return result

    def selected_index(self) -> int:
        """Indeks zaznaczonej pozycji na bieżącym poziomie."""
        return self._current()[1]

    def _move(self, delta: int) -> None:
        folder, index = self._current()
        count = len(folder.children) + 1  # zawsze >= 1 (pozycja systemowa)
        new_index = (index + delta) % count
        self._stack[-1] = (folder, new_index)

    def move_up(self) -> None:
        """Cyklicznie w górę (z pierwszej pozycji na ostatnią)."""
        self._move(-1)

    def move_down(self) -> None:
        """Cyklicznie w dół (z ostatniej pozycji na pierwszą)."""
        self._move(+1)

    def activate(self) -> NavigatorAction:
        """Aktywuje zaznaczoną pozycję; zwraca akcję dla pętli głównej."""
        entry = self.entries()[self.selected_index()]
        if entry.kind is EntryKind.FOLDER and isinstance(entry.node, Folder):
            # stan bieżącego poziomu zostaje na stosie - wrócimy do niego po Wstecz
            self._stack.append((entry.node, 0))
            return Stay()
        if entry.kind is EntryKind.BACK:
            assert len(self._stack) > 1
            self._stack.pop()
            return Stay()
        if entry.kind is EntryKind.EXIT:
            return Quit()
        assert entry.kind is EntryKind.SCRIPT and isinstance(entry.node, ScriptItem)
        # stan nawigacji się nie zmienia - po skrypcie wracamy na to samo miejsce
        return RunScript(item=entry.node, menu_path=self.breadcrumb())

    def breadcrumb(self) -> Tuple[str, ...]:
        """Nazwy folderów od roota (bez niego) do bieżącego poziomu."""
        return tuple(folder.name for folder, _ in self._stack[1:])

    def title(self) -> str:
        """Tytuł menu głównego (nazwa roota)."""
        return self._root.name

    def go_root(self) -> None:
        """Reset do menu głównego (czyści stos, zaznaczenie = 0)."""
        self._stack = [(self._root, 0)]
