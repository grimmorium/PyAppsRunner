"""Testy parsera i modelu konfiguracji XML (Krok 2 specyfikacji)."""

from pathlib import Path

import pytest

from menu_app.config import ConfigError, Folder, ScriptItem, load_menu, parse_menu
from menu_app.texts import DEFAULT_MENU_TITLE


SIMPLE_XML = """<?xml version="1.0" encoding="utf-8"?>
<menu title="Moje menu">
  <item name="Jeden" dir="scripts/a" file="a.py"/>
  <folder name="Folder A">
    <item name="Dwa" dir="scripts/b" file="b.py"/>
  </folder>
</menu>
"""


def test_simple_tree_structure() -> None:
    root = parse_menu(SIMPLE_XML)
    assert isinstance(root, Folder)
    assert root.name == "Moje menu"
    item1, folder_a = root.children
    assert item1 == ScriptItem(name="Jeden", directory="scripts/a", file="a.py")
    assert isinstance(folder_a, Folder)
    assert folder_a.name == "Folder A"
    (item2,) = folder_a.children
    assert item2 == ScriptItem(name="Dwa", directory="scripts/b", file="b.py")


def test_three_level_nesting_and_order_preserved() -> None:
    xml = """<menu>
      <folder name="Pierwszy">
        <item name="a" dir="d1" file="a.py"/>
        <folder name="Drugi">
          <item name="b" dir="d2" file="b.py"/>
          <folder name="Trzeci">
            <item name="c" dir="d3" file="c.py"/>
          </folder>
        </folder>
      </folder>
      <item name="ostatni" dir="d4" file="z.py"/>
    </menu>"""
    root = parse_menu(xml)
    first, last = root.children
    assert isinstance(first, Folder) and first.name == "Pierwszy"
    item_a, second = first.children
    assert item_a.name == "a"
    assert isinstance(second, Folder) and second.name == "Drugi"
    item_b, third = second.children
    assert item_b.name == "b"
    assert isinstance(third, Folder) and third.name == "Trzeci"
    (item_c,) = third.children
    assert item_c.file == "c.py"
    # kolejność w XML = kolejność w menu
    assert [type(n).__name__ for n in root.children] == ["Folder", "ScriptItem"]
    assert last.name == "ostatni"


def test_default_title() -> None:
    root = parse_menu('<menu><item name="x" dir="d" file="a.py"/></menu>')
    assert root.name == DEFAULT_MENU_TITLE


def test_custom_title() -> None:
    root = parse_menu(SIMPLE_XML)
    assert root.name == "Moje menu"


def test_empty_folder_allowed() -> None:
    root = parse_menu('<menu><folder name="Pusty"/></menu>')
    (folder,) = root.children
    assert folder.children == ()


def test_polish_characters_in_names() -> None:
    xml = '<menu title="Żółw"><item name="ą ę ł ż ś" dir="dż" file="ź.py"/></menu>'
    root = parse_menu(xml)
    assert root.name == "Żółw"
    (item,) = root.children
    assert item.name == "ą ę ł ż ś"


def test_case_insensitive_py_extension_ok() -> None:
    root = parse_menu('<menu><item name="x" dir="d" file="X.PY"/></menu>')
    (item,) = root.children
    assert item.file == "X.PY"


def test_unknown_attributes_ignored() -> None:
    xml = ('<menu title="t" extra="1">'
           '<item name="x" dir="d" file="a.py" nieznane="tak"/>'
           "</menu>")
    root = parse_menu(xml)
    (item,) = root.children
    assert item.name == "x"


def test_nonexistent_file_raises_config_error(tmp_path: Path) -> None:
    with pytest.raises(ConfigError):
        load_menu(tmp_path / "brak.xml")


def test_load_menu_reads_utf8_file(tmp_path: Path) -> None:
    xml = '<menu title="Polski"><item name="ż" dir="d" file="z.py"/></menu>'
    cfg = tmp_path / "menu.xml"
    cfg.write_text(xml, encoding="utf-8")
    root = load_menu(cfg)
    assert root.name == "Polski"


# --- przypadki błędów -> ConfigError ---

@pytest.mark.parametrize(
    "bad_xml",
    [
        '<menu><folder name="x"></menu>',              # niepoprawny XML (ParseError)
        "<notmenu/>",                                  # zły element główny
        '<menu><item dir="d" file="a.py"/></menu>',    # brak atrybutu name
        '<menu><item name="n" file="a.py"/></menu>',   # brak atrybutu dir
        '<menu><item name="n" dir="d"/></menu>',       # brak atrybutu file
        '<menu><folder/></menu>',                      # folder bez name
        '<menu><item name="" dir="d" file="a.py"/></menu>',      # pusty atrybut
        '<menu><item name="n" dir=" " file="a.py"/></menu>',     # pusty (spacja)
        '<menu><item name="n" dir="d" file="x.txt"/></menu>',    # zły typ pliku
        "<menu><widget/></menu>",                      # nieznany element w menu
        '<menu><folder name="f"><tajemnica/></folder></menu>',   # nieznany w folderze
        '<menu><item name="n" dir="d" file="a.py"><x/></item></menu>',  # item z dziećmi
    ],
)
def test_error_cases_raise_config_error(bad_xml: str) -> None:
    with pytest.raises(ConfigError):
        parse_menu(bad_xml)


def test_semantic_error_message_contains_line_number() -> None:
    xml = '<menu>\n  <item name="ok" dir="d" file="a.py"/>\n  <folder name="f">\n'
    with pytest.raises(ConfigError) as excinfo:
        parse_menu(xml)
    assert "linia" in str(excinfo.value).lower()


def test_bad_xml_error_message_not_empty() -> None:
    with pytest.raises(ConfigError) as excinfo:
        parse_menu("<menu><folder name='x'>")
    assert str(excinfo.value)
