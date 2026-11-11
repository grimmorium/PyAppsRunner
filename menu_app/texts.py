"""User interface text constants (English).

All user-visible messages are collected in this module.
Templates with {placeholder}s are filled using str.format().
"""

# Menu title and system entries
DEFAULT_MENU_TITLE = "Main Menu"
EXIT_LABEL = "Exit"
BACK_LABEL = "Back"

# Menu screen footer
FOOTER_TEXT = "a - up | z - down | Enter - confirm"

# Pause after a script finishes
PRESS_ENTER = "Press Enter to return to the menu"

# Interruption (Ctrl+C) during a script run
INTERRUPTED_MESSAGE = "Interrupted."

# --- XML configuration errors (menu_app/config.py) ---
ERR_CONFIG_FILE_NOT_FOUND = "Configuration file does not exist: {path}"
ERR_CONFIG_READ_ERROR = "Error reading the configuration file: {error}"
ERR_XML_PARSE = "Invalid XML ({detail})"
ERR_BAD_ROOT_ELEMENT = 'Bad root element: expected <menu>, found <{tag}>'
ERR_MISSING_ATTRIBUTE = "Missing attribute '{attr}' in element <{tag}>"
ERR_EMPTY_ATTRIBUTE = "Empty attribute '{attr}' in element <{tag}>"
ERR_ITEM_HAS_CHILDREN = '<item> cannot contain child elements (name: {name})'
ERR_UNKNOWN_ELEMENT = 'Unknown element <{tag}>'
ERR_BAD_FILE_EXTENSION = "The file attribute must point to a .py file, found: {value}"

# --- Script path errors (menu_app/paths.py) ---
ERR_ABSOLUTE_DIR = "Directory in the configuration must be relative, found: {dir}"
ERR_SCRIPT_OUTSIDE_BASE = "Script path escapes the base directory: {path}"
ERR_SCRIPT_NOT_FOUND = "Script file not found: {path}"

# --- Script contract errors (menu_app/runner.py) ---
ERR_NO_RUN_FUNCTION = "The script does not define a run(ctx) function"
ERR_BAD_RETURN_VALUE = "run() should return int or None"
SCRIPT_NONZERO_CODE = "Script finished with code: {code}"
ERR_MODULE_PREPARE = "Failed to prepare the script file for execution: {path}"

# --- Application messages (menu_app/app.py, main.py) ---
SCRIPT_ERROR_WITH_CODE = "Script error: {error} [exit code: {code}]"
MSG_CONFIG_ERROR = "Configuration error: {error}"
MSG_NO_TTY = "stdin is not a terminal - the application requires an interactive console"
