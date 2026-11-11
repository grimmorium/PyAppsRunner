"""Sample script demonstrating an error.

The menu should show an error message (with the exit code) and remain
fully functional - script exceptions do not propagate to the menu.
"""


def run(ctx):
    """Raises a deliberate exception to demonstrate error handling."""
    raise RuntimeError("Intentional demo error")
