"""Application entry point (a thin layer over menu_app.App) - Step 9.

Reads command-line arguments, loads the XML configuration and starts the
main loop. Exit codes: 0 = normal exit, 2 = configuration error,
3 = stdin is not a terminal (no interactive mode).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional, TextIO

from menu_app.app import App
from menu_app.config import ConfigError, load_menu
from menu_app.keys import KeyReader, create_key_reader
from menu_app.terminal import enable_ansi
from menu_app.texts import MSG_CONFIG_ERROR, MSG_NO_TTY


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Text menu that runs .py scripts (keys: a/z/Enter)."
    )
    default_base = Path(__file__).resolve().parent
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="path to the XML menu file (default <base-dir>/menu.xml)",
    )
    parser.add_argument(
        "--base-dir",
        dest="base_dir",
        type=Path,
        default=default_base,
        help="base directory for script paths from the XML (default: application directory)",
    )
    return parser


def main(argv: Optional[list[str]] = None, key_reader: Optional[KeyReader] = None, out: Optional[TextIO] = None) -> int:
    """Entry point; test parameters allow injecting I/O."""
    args = _build_parser().parse_args(argv)
    config_path: Path = args.config if args.config is not None else args.base_dir / "menu.xml"

    stream: TextIO = out if out is not None else sys.stdout
    if hasattr(stream, "reconfigure"):  # CPython stdout; under tests it may be a substitute
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (ValueError, OSError):
            pass
    enable_ansi()

    try:
        root = load_menu(config_path)
    except ConfigError as exc:
        print(MSG_CONFIG_ERROR.format(error=str(exc)), file=sys.stderr)
        return 2

    if key_reader is None and not sys.stdin.isatty():
        print(MSG_NO_TTY, file=sys.stderr)
        return 3

    app = App(
        root=root,
        base_dir=args.base_dir,
        key_reader=key_reader if key_reader is not None else create_key_reader(),
        out=stream,
    )
    return app.run()


if __name__ == "__main__":
    sys.exit(main())
