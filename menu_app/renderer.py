"""Building the menu screen text - a pure function without I/O (Step 6 of the specification).

Layout: header, "-" separator, entries ("> " = selected), blank line,
footer. The list fits in max(1, height - 5) lines; hidden parts are marked
with a "  ..." row. Lines longer than width are truncated to width-1
characters with an appended "…". The content contains no ANSI codes.
"""

from __future__ import annotations

from typing import List, Tuple

from .texts import FOOTER_TEXT

INDICATOR = "  ..."


def _fit(line: str, width: int) -> str:
    """Truncates a line longer than ``width`` (to width-1 chars + "…")."""
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
    """Builds the full screen text; every line ends with "\\n"."""
    header = title if not breadcrumb else " / ".join([title, *breadcrumb])

    total = len(labels)
    budget = max(1, height - 5)  # header 2 + blank 1 + footer 1 + spare 1
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
