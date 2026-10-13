"""Przykładowy skrypt powitalny - spełnia kontrakt run(ctx) z dokumentacji."""


def run(ctx):
    """Wypisuje powitanie oraz kontekst, w jakim skrypt został uruchomiony."""
    print("Witaj!")
    print(f"Ścieżka w menu: {ctx.menu_path}")
    print(f"Plik skryptu: {ctx.script_path}")
    return 0
