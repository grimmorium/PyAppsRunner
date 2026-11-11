"""Shared test configuration.

Adds the project directory to sys.path (if pytest does not see it) and
defines the `tmp_project` fixture building a mini-project in a temporary
directory: menu.xml + sample scripts fulfilling the Step 4 contract.
"""

import sys
from pathlib import Path

import pytest

PROJECT_DIR = Path(__file__).resolve().parents[1]
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))


MENU_XML_TEMPLATE = """<?xml version="1.0" encoding="utf-8"?>
<menu title="{title}">
  <item name="Marker" dir="scripts/basic" file="marker.py"/>
  <item name="Error demo" dir="scripts/basic" file="boom.py"/>
  <folder name="Tools">
    <folder name="Deep">
      <item name="To root" dir="scripts/tools" file="to_root.py"/>
      <item name="Deep script" dir="scripts/deep" file="deep.py"/>
    </folder>
  </folder>
</menu>
"""

# Each script fulfills the Step 4 contract (module-level run(ctx) function).
PROJECT_SCRIPTS = {
    "scripts/basic/marker.py": (
        'def run(ctx):\n'
        '    (ctx.base_dir / "marker.txt").write_text("ok", encoding="utf-8")\n'
        "    return 0\n"
    ),
    "scripts/basic/boom.py": (
        'def run(ctx):\n'
        '    raise RuntimeError("Intentional test error")\n'
    ),
    "scripts/tools/to_root.py": (
        'def run(ctx):\n'
        '    print("Returning to main menu")\n'
        "    ctx.exit_to_root()\n"
        "    return None\n"
    ),
    "scripts/deep/deep.py": (
        'def run(ctx):\n'
        '    print("Deep script works")\n'
        "    return 0\n"
    ),
}


@pytest.fixture
def tmp_project(tmp_path: Path) -> Path:
    """Mini-project in a temporary directory (menu.xml + scripts)."""
    for rel, content in PROJECT_SCRIPTS.items():
        script = tmp_path / rel
        script.parent.mkdir(parents=True, exist_ok=True)
        script.write_text(content, encoding="utf-8")
    xml_file = tmp_path / "menu.xml"
    xml_file.write_text(MENU_XML_TEMPLATE.format(title="Test menu"), encoding="utf-8")
    return tmp_path
