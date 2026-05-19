"""Verify dotenv package swap (v1.0.1) is import-compatible."""


def test_dotenv_load_dotenv_is_importable():
    from dotenv import load_dotenv

    assert callable(load_dotenv)


def test_dotenv_module_is_python_dotenv():
    from dotenv import load_dotenv

    assert "dotenv" in load_dotenv.__module__
