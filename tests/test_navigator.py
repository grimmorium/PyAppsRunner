"""Testy stanu nawigacji menu - czysta logika bez I/O (Krok 5 specyfikacji)."""

from menu_app.config import Folder, ScriptItem
from menu_app.navigator import EntryKind, Navigator, Quit, RunScript, Stay
from menu_app.texts import BACK_LABEL, EXIT_LABEL


def item(name: str) -> ScriptItem:
    return ScriptItem(name=name, directory="scripts", file=f"{name.lower()}.py")


ROOT = Folder(
    name="Menu główne",
    children=(
        item("Alfa"),
        item("Beta"),
        Folder(
            name="Narzędzia",
            children=(
                item("Gamma"),
                item("Delta"),
                Folder(name="Głęboko", children=(item("Epsilon"),)),
            ),
        ),
    ),
)


def test_root_entries_end_with_exit() -> None:
    nav = Navigator(ROOT)
    entries = nav.entries()
    assert [e.kind for e in entries] == [EntryKind.SCRIPT, EntryKind.SCRIPT, EntryKind.FOLDER, EntryKind.EXIT]
    assert entries[-1].label == EXIT_LABEL
    assert entries[-1].node is None


def test_submenu_entries_end_with_back() -> None:
    nav = Navigator(ROOT)
    nav.move_down()
    nav.move_down()  # na "Narzędzia" (indeks 2)
    action = nav.activate()
    assert isinstance(action, Stay)
    entries = nav.entries()
    assert [e.kind for e in entries] == [EntryKind.SCRIPT, EntryKind.SCRIPT, EntryKind.FOLDER, EntryKind.BACK]
    assert entries[-1].label == BACK_LABEL


def test_position_restored_after_back_at_three_levels() -> None:
    nav = Navigator(ROOT)
    # root: 0=Alfa 1=Beta 2=Narzędzia 3=Wyjście
    nav.move_down()
    nav.move_down()
    assert isinstance(nav.activate(), Stay)          # wchodzimy do Narzędzi (idx 2 zapamiętany)
    assert nav.breadcrumb() == ("Narzędzia",)
    assert nav.selected_index() == 0
    # Narzędzia: 0=Gamma 1=Delta 2=Głęboko 3=Wstecz
    nav.move_down()
    nav.move_down()                                  # na Głęboko (idx 2)
    assert isinstance(nav.activate(), Stay)          # wchodzimy do Głęboko
    assert nav.breadcrumb() == ("Narzędzia", "Głęboko")
    # Głęboko: 0=Epsilon 1=Wstecz -> wracamy
    nav.move_down()
    assert isinstance(nav.activate(), Stay)          # Wstecz do Narzędzi
    assert nav.breadcrumb() == ("Narzędzia",)
    assert nav.selected_index() == 2                 # pozycja przywrócona!
    # z powrotem do roota
    nav.move_down()                                  # na Wstecz (idx 3)
    assert isinstance(nav.activate(), Stay)          # Wstecz do roota
    assert nav.breadcrumb() == ()
    assert nav.selected_index() == 2                 # pozycja w root przywrócona


def test_cyclic_movement_up_and_down() -> None:
    nav = Navigator(ROOT)
    count = len(nav.entries())
    nav.move_up()
    assert nav.selected_index() == count - 1         # z pierwszego na ostatnie
    nav.move_down()
    assert nav.selected_index() == 0                 # i z powrotem


def test_empty_folder_contains_only_back() -> None:
    root = Folder(name="r", children=(Folder(name="Pusty", children=()),))
    nav = Navigator(root)
    nav.activate()                                   # wchodzimy do pustego folderu
    entries = nav.entries()
    assert [e.kind for e in entries] == [EntryKind.BACK]
    assert nav.selected_index() == 0
    # cykliczność na liście jednoelementowej nie rzuca wyjątkiem
    nav.move_up()
    nav.move_down()
    assert nav.selected_index() == 0


def test_root_without_children_has_only_exit() -> None:
    nav = Navigator(Folder(name="puste", children=()))
    entries = nav.entries()
    assert [e.kind for e in entries] == [EntryKind.EXIT]


def test_breadcrumb_and_title() -> None:
    nav = Navigator(ROOT)
    assert nav.title() == "Menu główne"
    assert nav.breadcrumb() == ()
    nav.move_down()
    nav.move_down()
    nav.activate()                                   # Narzędzia
    nav.move_down()
    nav.move_down()
    nav.activate()                                   # Głęboko
    assert nav.breadcrumb() == ("Narzędzia", "Głęboko")


def test_go_root_from_deep_level() -> None:
    nav = Navigator(ROOT)
    nav.move_down()
    nav.move_down()
    nav.activate()                                   # Narzędzia (idx 2 w root)
    nav.move_down()
    nav.move_down()                                  # na Głęboko (idx 2)
    nav.activate()                                   # wchodzimy do Głęboko
    assert len(nav.breadcrumb()) == 2
    nav.go_root()
    assert nav.breadcrumb() == ()
    assert nav.selected_index() == 0


def test_run_script_action_carries_menu_path() -> None:
    # skrypt w root -> menu_path puste
    nav = Navigator(ROOT)
    action = nav.activate()                          # Alfa (idx 0)
    assert isinstance(action, RunScript)
    assert action.item.name == "Alfa"
    assert action.menu_path == ()
    # stan nawigacji się nie zmienia po aktywnym skrypcie
    assert nav.breadcrumb() == ()

    # skrypt w podfolderze -> pełna ścieżka folderów
    nav2 = Navigator(ROOT)
    nav2.move_down()
    nav2.move_down()
    nav2.activate()                                  # Narzędzia (selekcja 0 = Gamma)
    action2 = nav2.activate()
    assert isinstance(action2, RunScript)
    assert action2.item.name == "Gamma"
    assert action2.menu_path == ("Narzędzia",)


def test_quit_only_from_exit() -> None:
    nav = Navigator(ROOT)
    # w podmenu ostatnia pozycja to Wstecz - nie może zwrócić Quit
    nav.move_down()
    nav.move_down()
    nav.activate()                                   # Narzędzia (selekcja wraca do 0)
    for _ in range(len(nav.entries()) - 1):          # na koniec listy (Wstecz, idx 3)
        nav.move_down()
    assert isinstance(nav.activate(), Stay)          # Wstecz, nie Quit
    assert nav.breadcrumb() == ()                    # wróciliśmy do roota
    assert nav.selected_index() == 2                 # pozycja w root przywrócona
    # tylko EXIT w root daje Quit (ostatnia pozycja, idx 3)
    nav.move_down()
    assert isinstance(nav.activate(), Quit)
