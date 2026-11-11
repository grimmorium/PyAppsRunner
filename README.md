# PyAppsRunner

A console application that renders a **multi-level, text-based menu** from an XML file and runs the selected Python scripts **in the same process**. Target platform is Linux; it is also tested on Windows. It uses only the Python standard library (Python ≥ 3.9) — `pytest` is required for tests only.

```
Main Menu / Tools
----------------------------------------
> Exit-to-root demo
  Advanced
    ...

a - up | z - down | Enter - confirm
```

## Features

- **XML-driven menu** — the whole tree (folders + scripts) is declared in `menu.xml`, with arbitrary nesting depth.
- **In-process script execution** — scripts run via `importlib` inside the same process, so a simple contract (`run(ctx)`) and context passing are possible. A crashing script never takes the menu down with it.
- **Cyclic navigation** — moving up from the first entry wraps to the last (and vice versa). Returning from a submenu restores the selection you had before entering it.
- **System entries** — every list ends with `Exit` (main menu) or `Back` (submenus); these are not part of the XML.
- **Path safety** — script paths must stay inside the base directory; absolute paths and `../` escapes are rejected.
- **Cross-platform key handling** — lazy imports of `termios`/`tty` (POSIX) and `msvcrt` (Windows), so the shared modules import cleanly on both systems.
- **Testable core** — keyboard, screen, script runner and pause are all injected, so the logic is fully testable without a real terminal.

## Requirements

- Python ≥ 3.9 (standard library only)
- An interactive console (`stdin` must be a TTY). With redirected `stdin`, the program exits with code `3`.

## Running the application

```bash
python main.py                          # menu from <app-dir>/menu.xml
python main.py --config path/to/menu.xml
python main.py --base-dir DIR           # base dir for script paths in the XML
                                        # (default: directory containing main.py)
```

### Command-line options

| Option | Default | Description |
|--------|---------|-------------|
| `--config PATH` | `<base-dir>/menu.xml` | Path to the XML menu file. |
| `--base-dir DIR` | Directory of `main.py` | Base directory that all relative script paths in the XML are resolved against. |

### Exit codes

| Code | Meaning |
|------|---------|
| `0` | Normal exit, or `Ctrl+C` pressed while in a menu. |
| `2` | XML configuration error (missing file, malformed XML, invalid element/attribute). |
| `3` | `stdin` is not an interactive terminal and no key reader was injected. |

## Keyboard controls

| Key | Action |
|-----|--------|
| `a` / `A` | Move **up** (cyclic — from the first entry to the last). |
| `z` / `Z` | Move **down** (cyclic). |
| `Enter` | Confirm: enter a submenu, run a script, or exit. |
| `Ctrl+C` | In a menu: clean exit (code 0). During a script: interrupt it and return to the menu. During the "Press Enter…" pause: ends only the pause. |

Any other key is ignored; arrow-key / ESC escape sequences are treated as "other". The selected entry is always kept visible — long lists scroll with `...` indicators at the hidden edges.

## Configuration format (`menu.xml`)

```xml
<?xml version="1.0" encoding="utf-8"?>
<menu title="Main Menu">
  <item name="Greeting" dir="scripts/basic" file="hello.py"/>
  <folder name="Tools">
    <item name="Exit-to-root demo" dir="scripts/tools" file="exit_to_root_demo.py"/>
    <folder name="Advanced">
      <item name="Error test" dir="scripts/basic" file="error_demo.py"/>
    </folder>
  </folder>
</menu>
```

### Rules

- The root element is `<menu>`; the `title` attribute is optional (defaults to `"Main Menu"`).
- `<item name dir file/>` — all three attributes are required and non-empty. An `<item>` cannot have children, and `file` must end in `.py` (case-insensitive).
- `<folder name>` may contain folders and items at any depth; an empty folder is allowed.
- Element order in the XML = entry order in the menu.
- `dir` is a path **relative to the base directory** (`\` separators are accepted and normalized to `/`). The resolved result must stay inside the base directory (protection against `../`).
- Unknown elements are a configuration error; unknown attributes are ignored.
- Error messages include the line number when it can be determined.

> A script file's existence is checked **at run time**, not while reading the XML — so the menu still works if a script is missing, and you get an error message only after selecting that entry.

## Script contract

A script is an ordinary `.py` file containing a module-level function:

```python
def run(ctx) -> int | None:
    ...
```

1. **Return value:** `None` or `0` = success; any other integer = error (the menu shows the code). Non-integer values (e.g. text, bool) are a contract violation.
2. **Returning to the menu** is simply finishing `run()`. Also allowed: `sys.exit(n)` (treated as `return n`) and `Ctrl+C` (an interruption — reported as "Interrupted.", not an error).
3. Module-level code outside `run()` should be side-effect free (importing must be clean); every run is a fresh execution of the file (the module is removed from `sys.modules` afterwards).
4. A script uses ordinary `print()` / `input()` — the terminal is in normal mode; its exceptions are caught (traceback on stderr) and never shut down the menu.
5. The script's directory is added to the front of `sys.path` for the duration of the run, so it can import sibling modules. A script does **not** change the process working directory.

Minimal template:

```python
def run(ctx):
    print("My action")
    return 0
```

### The `ctx` context (`ScriptContext` dataclass)

| Field | Meaning |
|-------|---------|
| `base_dir: Path` | Application base directory. |
| `script_path: Path` | Full path of the file being run. |
| `script_dir: Path` | Directory containing the script. |
| `menu_path: tuple[str, ...]` | Folder names leading to the entry (without root), e.g. `("Tools", "Advanced")`. |
| `skip_pause: bool = False` | `True` → no "Press Enter…" pause after the script. |

Methods:

- `ctx.exit_to_root()` — after finishing, the menu returns to the **main** menu instead of the level that launched the script.
- `ctx.pause(message=...)` — a user-facing pause mid-script (`input`; EOF is ignored).

After a script finishes (unless `skip_pause=True`) the program shows "Press Enter to return to the menu" and comes back to the same level with the same selection. A pause also follows errors (missing file, path outside base, failing script) so you have time to read the message.

## Sample scripts

- `scripts/basic/hello.py` — greeting + prints its context;
- `scripts/basic/error_demo.py` — raises a deliberate exception (demonstrates error handling);
- `scripts/tools/exit_to_root_demo.py` — demonstrates `ctx.exit_to_root()`.

## Project structure

```
PyAppsRunner/
├── main.py                  # entry point (thin, arguments only)
├── menu.xml                 # sample configuration
├── requirements-dev.txt     # contains: pytest
├── App_desc.txt             # original step-by-step specification
├── menu_app/
│   ├── __init__.py
│   ├── texts.py             # UI text constants (single source of user-facing strings)
│   ├── config.py            # data model + XML parser + validation
│   ├── paths.py             # script path resolution & safety checks
│   ├── script_api.py        # ScriptContext (the script contract)
│   ├── runner.py            # loading and running scripts in-process
│   ├── navigator.py         # navigation state (no I/O)
│   ├── renderer.py          # screen text building (no I/O)
│   ├── keys.py              # key reading (Linux/Windows, lazy imports)
│   ├── terminal.py          # screen clearing, ANSI, window size
│   ├── app.py               # main loop (ties everything together)
│   └── testing.py           # FakeKeyReader for tests
├── scripts/                 # sample scripts
│   ├── basic/hello.py
│   ├── basic/error_demo.py
│   └── tools/exit_to_root_demo.py
└── tests/                   # pytest suite (TDD — every step kept it green)
```

## Running the tests

```bash
pip install -r requirements-dev.txt   # installs pytest
python -m pytest -q                   # full test suite
```

Platform-dependent tests (e.g. the POSIX pseudoterminal `pty` ones) are skipped on systems where they cannot run (`pytest.mark.skipif`).

## Design decisions

From the specification:

1. Base directory = the directory of `main.py`; overridable via `--base-dir`.
2. Cyclic navigation up and down.
3. System entries `Exit` (root) / `Back` (submenus), always at the end of a list.
4. Scripts run in the same process (`importlib`); script errors never shut down the menu.
5. After a script, return to the level that launched it; optionally `ctx.exit_to_root()`.
6. "Press Enter…" pause after a script unless `skip_pause=True`.
7. `Ctrl+C` in a menu = clean exit (code 0); `Ctrl+C` in a script = interrupt and return to the menu.

Additional implementation decisions:

1. **Bool as a return value** is treated as a contract violation (`run() should return int or None`) even though `True/False` are `int` subclasses; likewise `sys.exit(True)` yields code 1.
2. **Line numbers in XML errors** — ElementTree does not expose line numbers for semantic errors, so a raw-text scan plus an `ET.TreeBuilder` subclass records where each tag starts. Messages end with ", line N" when available.
3. **Pause after errors too** (run failure, missing file, path outside base) so the user can read the message; skipped only via `skip_pause=True`, which a script sets itself and therefore does not apply to pre-run errors.
4. **`Ctrl+C` / EOF during a pause** ends only the pause and returns to the menu (it never kills the app).
5. **OTHER keys are ignored** — the screen is redrawn but state is unchanged; escape sequences map to OTHER as well.
6. **Renderer viewport** = `max(1, height - 5)` lines; hidden sides are marked with a `...` row; very small windows (width < 10, height < 6) never raise — at least one entry line is shown.
7. **`FakeKeyReader`** lives in `menu_app/testing.py`; once its key list is exhausted it raises `AssertionError`, guarding tests against an infinite loop.
8. **Exit codes from `main()`:** 2 = XML configuration error, 3 = `stdin` is not a terminal and no key reader was injected (e.g. running under CI without a TTY).
9. **Windows:** stdout is switched to UTF-8 (`reconfigure`, when available) and ANSI codes are enabled via `SetConsoleMode` (ctypes); failure with redirected stdout is silently ignored. On POSIX, `enable_ansi()` is a no-op.
10. **Script module name** = `menu_script_<sha256(path)[:16]>` — unique per file so two scripts with the same filename in different directories never collide; the module is removed from `sys.modules` after every run.
