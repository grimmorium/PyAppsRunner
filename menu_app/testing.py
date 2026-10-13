"""Pomocnicze klasy do testów (wstrzykiwane zamiast prawdziwego I/O).

Dozwolona lokalizacja FakeKeyReader zgodnie z Krokiem 7 specyfikacji.
"""

from __future__ import annotations

from typing import List, Sequence

from .keys import Key


class FakeKeyReader:
    """Zwraca klawisze z podanej listy po kolei (FIFO).

    Po wyczerpaniu rzuca AssertionError - zabezpiecza testy przed
    nieskończoną pętlą aplikacji.
    """

    def __init__(self, keys: Sequence[Key]) -> None:
        self._keys: List[Key] = list(keys)

    def read_key(self) -> Key:
        if not self._keys:
            raise AssertionError("brak kolejnych klawiszy")
        return self._keys.pop(0)
