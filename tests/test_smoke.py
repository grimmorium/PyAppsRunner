"""Smoke test: the menu_app package can be imported (Step 1 Definition of Done)."""


def test_menu_app_imports() -> None:
    import menu_app

    assert menu_app is not None
