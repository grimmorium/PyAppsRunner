"""Menu navigation state - pure logic without I/O (Step 5 of the specification).

Navigation is cyclic; at the end of every list there is a system entry
(EXIT in root, BACK in submenus). Returning from a submenu restores the
selection that was saved before entering it.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Tuple, Union

from .config import Folder, MenuNode, ScriptItem
from .texts import BACK_LABEL, EXIT_LABEL


class EntryKind(Enum):
    """Menu entry kind."""

    FOLDER = "folder"
    SCRIPT = "script"
    BACK = "back"
    EXIT = "exit"


@dataclass(frozen=True)
class Entry:
    """Menu list entry (folder children + system entry)."""

    kind: EntryKind
    label: str
    node: Optional[MenuNode]  # Folder or ScriptItem; None for BACK/EXIT


@dataclass(frozen=True)
class Stay:
    """Nothing happens - the loop draws the next screen."""


@dataclass(frozen=True)
class RunScript:
    """Run the script from the entry indicated by menu_path."""

    item: ScriptItem
    menu_path: Tuple[str, ...]


@dataclass(frozen=True)
class Quit:
    """Quit the program (exit code 0)."""


NavigatorAction = Union[Stay, RunScript, Quit]


class Navigator:
    """Navigation state: folder stack + selection per level."""

    def __init__(self, root: Folder) -> None:
        self._root = root
        # (folder, selected index); top of the stack = current level
        self._stack: List[Tuple[Folder, int]] = [(root, 0)]

    def _current(self) -> Tuple[Folder, int]:
        return self._stack[-1]

    def entries(self) -> list[Entry]:
        """Children of the current folder + system entry at the end."""
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
        """Index of the selected entry at the current level."""
        return self._current()[1]

    def _move(self, delta: int) -> None:
        folder, index = self._current()
        count = len(folder.children) + 1  # always >= 1 (system entry)
        new_index = (index + delta) % count
        self._stack[-1] = (folder, new_index)

    def move_up(self) -> None:
        """Cyclically up (from the first entry to the last)."""
        self._move(-1)

    def move_down(self) -> None:
        """Cyclically down (from the last entry to the first)."""
        self._move(+1)

    def activate(self) -> NavigatorAction:
        """Activates the selected entry; returns an action for the main loop."""
        entry = self.entries()[self.selected_index()]
        if entry.kind is EntryKind.FOLDER and isinstance(entry.node, Folder):
            # current level state stays on the stack - we return to it after Back
            self._stack.append((entry.node, 0))
            return Stay()
        if entry.kind is EntryKind.BACK:
            assert len(self._stack) > 1
            self._stack.pop()
            return Stay()
        if entry.kind is EntryKind.EXIT:
            return Quit()
        assert entry.kind is EntryKind.SCRIPT and isinstance(entry.node, ScriptItem)
        # navigation state does not change - after the script we come back to this spot
        return RunScript(item=entry.node, menu_path=self.breadcrumb())

    def breadcrumb(self) -> Tuple[str, ...]:
        """Folder names from root (excluding it) down to the current level."""
        return tuple(folder.name for folder, _ in self._stack[1:])

    def title(self) -> str:
        """Main menu title (root name)."""
        return self._root.name

    def go_root(self) -> None:
        """Reset to the main menu (clears the stack, selection = 0)."""
        self._stack = [(self._root, 0)]
