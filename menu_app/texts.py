"""Stałe teksty interfejsu użytkownika (po polsku).

Wszystkie komunikaty widoczne dla użytkownika są zebrane w tym module.
Szablony z {placeholder}ami wypełnia się metodą str.format().
"""

# Tytuł i pozycje systemowe menu
DEFAULT_MENU_TITLE = "Menu główne"
EXIT_LABEL = "Wyjście"
BACK_LABEL = "Wstecz"

# Stopka ekranu menu
FOOTER_TEXT = "a - góra | z - dół | Enter - zatwierdź"

# Pauza po zakończeniu skryptu
PRESS_ENTER = "Naciśnij Enter, aby wrócić do menu"

# Przerwanie (Ctrl+C) w trakcie skryptu
INTERRUPTED_MESSAGE = "Przerwano."

# --- Błędy konfiguracji XML (menu_app/config.py) ---
ERR_CONFIG_FILE_NOT_FOUND = "Plik konfiguracyjny nie istnieje: {path}"
ERR_CONFIG_READ_ERROR = "Błąd odczytu pliku konfiguracyjnego: {error}"
ERR_XML_PARSE = "Niepoprawny XML ({detail})"
ERR_BAD_ROOT_ELEMENT = 'Zły element główny: oczekiwano <menu>, znaleziono <{tag}>'
ERR_MISSING_ATTRIBUTE = "Brak atrybutu '{attr}' w elemencie <{tag}>"
ERR_EMPTY_ATTRIBUTE = "Pusty atrybut '{attr}' w elemencie <{tag}>"
ERR_ITEM_HAS_CHILDREN = 'Element <item> nie może zawierać podelementów (nazwa: {name})'
ERR_UNKNOWN_ELEMENT = 'Nieznany element <{tag}>'
ERR_BAD_FILE_EXTENSION = "Atrybut file musi wskazywać plik .py, znaleziono: {value}"

# --- Błędy ścieżek skryptów (menu_app/paths.py) ---
ERR_ABSOLUTE_DIR = "Katalog w konfiguracji musi być relatywny, znaleziono: {dir}"
ERR_SCRIPT_OUTSIDE_BASE = "Ścieżka skryptu wychodzi poza katalog bazowy: {path}"
ERR_SCRIPT_NOT_FOUND = "Nie znaleziono pliku skryptu: {path}"

# --- Błędy kontraktu skryptu (menu_app/runner.py) ---
ERR_NO_RUN_FUNCTION = "Skrypt nie definiuje funkcji run(ctx)"
ERR_BAD_RETURN_VALUE = "run() powinno zwrócić int lub None"
SCRIPT_NONZERO_CODE = "Skrypt zakończony kodem: {code}"
ERR_MODULE_PREPARE = "Nie udało się przygotować pliku skryptu do wykonania: {path}"

# --- Komunikaty aplikacji (menu_app/app.py, main.py) ---
SCRIPT_ERROR_WITH_CODE = "Błąd skryptu: {error} [kod wyjścia: {code}]"
MSG_CONFIG_ERROR = "Błąd konfiguracji: {error}"
MSG_NO_TTY = "stdin nie jest terminalem - aplikacja wymaga interaktywnej konsoli"
