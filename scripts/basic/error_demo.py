"""Przykładowy skrypt demonstrujący błąd.

Menu powinno pokazać komunikat o błędzie (z kodem wyjścia) i pozostać
w pełni działające - wyjątki skrypty nie propagują się do menu.
"""


def run(ctx):
    """Rzuca celowy wyjątek w celu demonstracji obsługi błędów."""
    raise RuntimeError("Celowy błąd demonstracyjny")
