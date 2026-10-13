"""Wspólna konfiguracja testów.

Dodaje katalog projektu do sys.path (jeśli pytest go nie widzi) oraz
definiuje fixture `tmp_project` budującą mini-projekt w katalogu
tymczasowym: menu.xml + przykładowe skrypty spełniające kontrakt z Kroku 4.
"""

import sys
from pathlib import Path

import pytest

PROJECT_DIR = Path(__file__).resolve().parents[1]
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))


MENU_XML_TEMPLATE = """<?xml version="1.0" encoding="utf-8"?>
<menu title="{title}">
  <item name="Znacznik" dir="scripts/basic" file="marker.py"/>
  <item name="Błęd demo" dir="scripts/basic" file="boom.py"/>
  <folder name="Narzędzia">
    <folder name="Głęboko">
      <item name="Do roota" dir="scripts/tools" file="to_root.py"/>
      <item name="Głęboki skrypt" dir="scripts/deep" file="deep.py"/>
    </folder>
  </folder>
</menu>
"""

# Każdy skrypt spełnia kontrakt z Kroku 4 (funkcja run(ctx) na poziomie modułu).
PROJECT_SCRIPTS = {
    "scripts/basic/marker.py": (
        'def run(ctx):\n'
        '    (ctx.base_dir / "marker.txt").write_text("ok", encoding="utf-8")\n'
        "    return 0\n"
    ),
    "scripts/basic/boom.py": (
        'def run(ctx):\n'
        '    raise RuntimeError("Celowy błąd testowy")\n'
    ),
    "scripts/tools/to_root.py": (
        'def run(ctx):\n'
        '    print("Zwracam do menu glownego")\n'
        "    ctx.exit_to_root()\n"
        "    return None\n"
    ),
    "scripts/deep/deep.py": (
        'def run(ctx):\n'
        '    print("Gleboki skrypt dziala")\n'
        "    return 0\n"
    ),
}


@pytest.fixture
def tmp_project(tmp_path: Path) -> Path:
    """Mini-projekt w katalogu tymczasowym (menu.xml + skrypty)."""
    for rel, content in PROJECT_SCRIPTS.items():
        script = tmp_path / rel
        script.parent.mkdir(parents=True, exist_ok=True)
        script.write_text(content, encoding="utf-8")
    xml_file = tmp_path / "menu.xml"
    xml_file.write_text(MENU_XML_TEMPLATE.format(title="Menu testowe"), encoding="utf-8")
    return tmp_path
