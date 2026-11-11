"""Tests of the menu navigation state - pure logic without I/O (Step 5 of the specification)."""

from menu_app.config import Folder, ScriptItem
from menu_app.navigator import EntryKind, Navigator, Quit, RunScript, Stay
from menu_app.texts import BACK_LABEL, EXIT_LABEL


def item(name: str) -> ScriptItem:
    return ScriptItem(name=name, directory="scripts", file=f"{name.lower()}.py")


ROOT = Folder(
    name="Main Menu",
    children=(
        item("Alfa"),
        item("Beta"),
        Folder(
            name="Tools",
            children=(
                item("Gamma"),
                item("Delta"),
                Folder(name="Deep", children=(item("Epsilon"),)),
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
    nav.move_down()  # onto "Tools" (index 2)
    action = nav.activate()
    assert isinstance(action, Stay)
    entries = nav.entries()
    assert [e.kind for e in entries] == [EntryKind.SCRIPT, EntryKind.SCRIPT, EntryKind.FOLDER, EntryKind.BACK]
    assert entries[-1].label == BACK_LABEL


def test_position_restored_after_back_at_three_levels() -> None:
    nav = Navigator(ROOT)
    # root: 0=Alfa 1=Beta 2=Tools 3=Exit
    nav.move_down()
    nav.move_down()
    assert isinstance(nav.activate(), Stay)          # enter Tools (idx 2 remembered)
    assert nav.breadcrumb() == ("Tools",)
    assert nav.selected_index() == 0
    # Tools: 0=Gamma 1=Delta 2=Deep 3=Back
    nav.move_down()
    nav.move_down()                                  # onto Deep (idx 2)
    assert isinstance(nav.activate(), Stay)          # enter Deep
    assert nav.breadcrumb() == ("Tools", "Deep")
    # Deep: 0=Epsilon 1=Back -> go back
    nav.move_down()
    assert isinstance(nav.activate(), Stay)          # Back to Tools
    assert nav.breadcrumb() == ("Tools",)
    assert nav.selected_index() == 2                 # position restored!
    # back to root
    nav.move_down()                                  # onto Back (idx 3)
    assert isinstance(nav.activate(), Stay)          # Back to root
    assert nav.breadcrumb() == ()
    assert nav.selected_index() == 2                 # root position restored


def test_cyclic_movement_up_and_down() -> None:
    nav = Navigator(ROOT)
    count = len(nav.entries())
    nav.move_up()
    assert nav.selected_index() == count - 1         # from the first to the last
    nav.move_down()
    assert nav.selected_index() == 0                 # and back


def test_empty_folder_contains_only_back() -> None:
    root = Folder(name="r", children=(Folder(name="Empty", children=()),))
    nav = Navigator(root)
    nav.activate()                                   # enter the empty folder
    entries = nav.entries()
    assert [e.kind for e in entries] == [EntryKind.BACK]
    assert nav.selected_index() == 0
    # cyclic movement on a one-element list does not raise
    nav.move_up()
    nav.move_down()
    assert nav.selected_index() == 0


def test_root_without_children_has_only_exit() -> None:
    nav = Navigator(Folder(name="empty", children=()))
    entries = nav.entries()
    assert [e.kind for e in entries] == [EntryKind.EXIT]


def test_breadcrumb_and_title() -> None:
    nav = Navigator(ROOT)
    assert nav.title() == "Main Menu"
    assert nav.breadcrumb() == ()
    nav.move_down()
    nav.move_down()
    nav.activate()                                   # Tools
    nav.move_down()
    nav.move_down()
    nav.activate()                                   # Deep
    assert nav.breadcrumb() == ("Tools", "Deep")


def test_go_root_from_deep_level() -> None:
    nav = Navigator(ROOT)
    nav.move_down()
    nav.move_down()
    nav.activate()                                   # Tools (idx 2 in root)
    nav.move_down()
    nav.move_down()                                  # onto Deep (idx 2)
    nav.activate()                                   # enter Deep
    assert len(nav.breadcrumb()) == 2
    nav.go_root()
    assert nav.breadcrumb() == ()
    assert nav.selected_index() == 0


def test_run_script_action_carries_menu_path() -> None:
    # script in root -> empty menu_path
    nav = Navigator(ROOT)
    action = nav.activate()                          # Alfa (idx 0)
    assert isinstance(action, RunScript)
    assert action.item.name == "Alfa"
    assert action.menu_path == ()
    # navigation state does not change after an active script
    assert nav.breadcrumb() == ()

    # script in a subfolder -> full folder path
    nav2 = Navigator(ROOT)
    nav2.move_down()
    nav2.move_down()
    nav2.activate()                                  # Tools (selection 0 = Gamma)
    action2 = nav2.activate()
    assert isinstance(action2, RunScript)
    assert action2.item.name == "Gamma"
    assert action2.menu_path == ("Tools",)


def test_quit_only_from_exit() -> None:
    nav = Navigator(ROOT)
    # in a submenu the last entry is Back - it must not return Quit
    nav.move_down()
    nav.move_down()
    nav.activate()                                   # Tools (selection returns to 0)
    for _ in range(len(nav.entries()) - 1):          # to the end of the list (Back, idx 3)
        nav.move_down()
    assert isinstance(nav.activate(), Stay)          # Back, not Quit
    assert nav.breadcrumb() == ()                    # we are back at root
    assert nav.selected_index() == 2                 # root position restored
    # only EXIT in root gives Quit (last entry, idx 3)
    nav.move_down()
    assert isinstance(nav.activate(), Quit)
