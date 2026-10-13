"""Budowa tekstu ekranu menu - czysta funkcja bez I/O (Krok 6 specyfikacji).

Układ: nagłówek, separator "-", pozycje ("> " = zaznaczona), pusta linia,
stopka. Lista mieści się w oknie max(1, height - 5) linii; ukryte części
oznacza wiersz "  ...". Linie dłuższe niż width obcina się do width-1
znaków i dopisuje "…". Treść nie zawiera kodów ANSI.
"""

from __future__ import annotations

from typing import List, Tuple

from .texts import FOOTER_TEXT

INDICATOR = "  ..."


def _fit(line: str, width: int) -> str:
    """Odcina linię dłuższą niż ``width`` (do width-1 znaków + „…")."""
    if len(line) > width:
        return line[: max(width - 1, 0)] + "…"
    return line


def render_screen(
    title: str,
    breadcrumb: Tuple[str, ...],
    labels: list[str],
    selected: int,
    width: int,
    height: int,
) -> str:
    """Buduje pełny tekst ekranu; każda linia kończy się „\\n"."""
    header = title if not breadcrumb else " / ".join([title, *breadcrumb])

    total = len(labels)
    budget = max(1, height - 5)  # nagłówek 2 + pusta 1 + stopka 1 + zapas 1
    start, end = 0, total
    if total > budget:
        entries_count = max(1, budget - 2) if budget >= 3 else 1
        start = selected - (entries_count // 2)
        start = max(0, min(start, total - entries_count))
        end = start + entries_count

    lines: List[str] = [_fit(header, width), _fit("-" * min(width, 40), width)]
    if start > 0:
        lines.append(INDICATOR)
    for index in range(start, end):
        prefix = "> " if index == selected else "  "
        lines.append(_fit(prefix + labels[index], width))
    if end < total:
        lines.append(INDICATOR)
    lines.append("")
    lines.append(_fit(FOOTER_TEXT, width))

    return "\n".join(lines) + "\n"
