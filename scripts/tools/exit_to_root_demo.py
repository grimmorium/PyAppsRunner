"""Sample script demonstrating the return to the main menu.

After run() finishes, the menu returns not to the level from which the
script was launched, but directly to the main menu (ctx.exit_to_root()).
"""


def run(ctx):
    """Announces the return and sets the exit_to_root flag."""
    print("Returning to the main menu")
    ctx.exit_to_root()
    return None
