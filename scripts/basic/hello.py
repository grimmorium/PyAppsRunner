"""Sample greeting script - fulfills the run(ctx) contract from the documentation."""


def run(ctx):
    """Prints a greeting and the context in which the script was launched."""
    print("Hello!")
    print(f"Menu path: {ctx.menu_path}")
    print(f"Script file: {ctx.script_path}")
    return 0
