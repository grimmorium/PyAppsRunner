"""Data model and XML configuration file parser (Step 2 of the specification).

Format: <menu title="..."> with arbitrarily nested <folder> elements and
leaf <item name dir file/> entries. Order in the XML = order in the menu.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple, Union

from .texts import (
    DEFAULT_MENU_TITLE,
    ERR_BAD_FILE_EXTENSION,
    ERR_BAD_ROOT_ELEMENT,
    ERR_CONFIG_FILE_NOT_FOUND,
    ERR_CONFIG_READ_ERROR,
    ERR_EMPTY_ATTRIBUTE,
    ERR_ITEM_HAS_CHILDREN,
    ERR_MISSING_ATTRIBUTE,
    ERR_UNKNOWN_ELEMENT,
    ERR_XML_PARSE,
)


@dataclass(frozen=True)
class ScriptItem:
    """Menu entry that launches a Python script."""

    name: str
    directory: str  # value of the dir attribute (relative to the base directory)
    file: str


@dataclass(frozen=True)
class Folder:
    """Folder (submenu). The root carries the menu title in its ``name`` field."""

    name: str
    children: Tuple["MenuNode", ...]


MenuNode = Union[Folder, ScriptItem]


class ConfigError(Exception):
    """XML configuration file error with a clear message."""


_START_TAG_RE = re.compile(r"<([A-Za-z_][A-Za-z0-9_.\-:]*)")


def _tag_lines(xml_text: str) -> Dict[str, List[int]]:
    """Map of tag -> line numbers of opening tags (document order).

    A closing tag </x> does not match the pattern; raw '<' is disallowed in
    attribute values by XML, so matches correspond exactly to opening tags.
    """
    lines: Dict[str, List[int]] = {}
    for match in _START_TAG_RE.finditer(xml_text):
        tag = match.group(1)
        line_no = xml_text.count("\n", 0, match.start()) + 1
        lines.setdefault(tag, []).append(line_no)
    return lines


class _LineRecordingBuilder(ET.TreeBuilder):
    """TreeBuilder recording element line numbers (for error messages)."""

    def __init__(self, tag_lines: Dict[str, List[int]]) -> None:
        super().__init__()
        self._tag_lines = tag_lines
        self._counters: Dict[str, int] = {}
        self.line_of: Dict[int, int] = {}

    def start(self, tag, attrs):  # type: ignore[override]
        elem = super().start(tag, attrs)
        queue = self._tag_lines.get(tag)
        if queue:
            index = min(self._counters.get(tag, 0), len(queue) - 1)
            self.line_of[id(elem)] = queue[index]
        self._counters[tag] = self._counters.get(tag, 0) + 1
        return elem


def parse_menu(xml_text: str) -> Folder:
    """Builds the menu tree from XML text; root has ``name`` equal to the title."""
    builder = _LineRecordingBuilder(_tag_lines(xml_text))
    parser = ET.XMLParser(target=builder)
    try:
        parser.feed(xml_text)
        root_elem = parser.close()
    except ET.ParseError as exc:
        position = getattr(exc, "position", None)
        if isinstance(position, tuple) and len(position) >= 2:
            detail = f"{exc.msg}, line {position[0]}, column {position[1]}"
        else:
            detail = str(exc)
        raise ConfigError(ERR_XML_PARSE.format(detail=detail)) from exc

    def line_suffix(elem: ET.Element) -> str:
        line_no = builder.line_of.get(id(elem))
        return f", line {line_no}" if line_no is not None else ""

    if root_elem.tag != "menu":
        raise ConfigError(ERR_BAD_ROOT_ELEMENT.format(tag=root_elem.tag) + line_suffix(root_elem))

    title = root_elem.get("title") or DEFAULT_MENU_TITLE

    def required_attr(elem: ET.Element, tag_label: str, attr: str) -> str:
        value = elem.get(attr)
        if value is None:
            raise ConfigError(ERR_MISSING_ATTRIBUTE.format(attr=attr, tag=tag_label) + line_suffix(elem))
        if not value.strip():
            raise ConfigError(ERR_EMPTY_ATTRIBUTE.format(attr=attr, tag=tag_label) + line_suffix(elem))
        return value

    def build_children(parent: ET.Element) -> Tuple[MenuNode, ...]:
        children: List[MenuNode] = []
        for child in parent:
            if child.tag == "folder":
                name = required_attr(child, "folder", "name")
                children.append(Folder(name=name, children=build_children(child)))
            elif child.tag == "item":
                item_name = required_attr(child, "item", "name")
                directory = required_attr(child, "item", "dir")
                file_name = required_attr(child, "item", "file")
                if len(child) > 0:
                    raise ConfigError(ERR_ITEM_HAS_CHILDREN.format(name=item_name) + line_suffix(child))
                if not file_name.lower().endswith(".py"):
                    raise ConfigError(ERR_BAD_FILE_EXTENSION.format(value=file_name) + line_suffix(child))
                children.append(ScriptItem(name=item_name, directory=directory, file=file_name))
            else:
                raise ConfigError(ERR_UNKNOWN_ELEMENT.format(tag=child.tag) + line_suffix(child))
        return tuple(children)

    return Folder(name=title, children=build_children(root_elem))


def load_menu(xml_path: Path) -> Folder:
    """Reads and parses the configuration file; returns root (name = title)."""
    path = Path(xml_path)
    if not path.exists():
        raise ConfigError(ERR_CONFIG_FILE_NOT_FOUND.format(path=str(path)))
    try:
        xml_text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise ConfigError(ERR_CONFIG_READ_ERROR.format(error=exc)) from exc
    return parse_menu(xml_text)
