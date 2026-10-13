"""Przykładowy skrypt demonstrujący powrót do menu głównego.

Po zakończeniu run() menu wraca nie na poziom, z którego uruchomiono
skrypt, lecz bezpośrednio do menu głównego (ctx.exit_to_root()).
"""


def run(ctx):
    """Informuje o powrocie i ustawia flagę exit_to_root."""
    print("Wracam do menu głównego")
    ctx.exit_to_root()
    return None
