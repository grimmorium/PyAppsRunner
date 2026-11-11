"""Helper classes for tests (injected instead of real I/O).

Allowed location for FakeKeyReader per Step 7 of the specification.
"""

from __future__ import annotations

from typing import List, Sequence

from .keys import Key


class FakeKeyReader:
    """Returns keys from a given list in order (FIFO).

    Raises AssertionError once exhausted - protects tests against an
    infinite application loop.
    """

    def __init__(self, keys: Sequence[Key]) -> None:
        self._keys: List[Key] = list(keys)

    def read_key(self) -> Key:
        if not self._keys:
            raise AssertionError("no more keys")
        return self._keys.pop(0)
