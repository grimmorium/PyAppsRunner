"""Test dymny: pakiet menu_app można zaimportować (Definition of Done Kroku 1)."""


def test_menu_app_imports() -> None:
    import menu_app

    assert menu_app is not None
