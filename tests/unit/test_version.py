# tests/unit/test_version.py
from src.equity_model import __version__, get_version, is_stable


def test_version_format():
    assert __version__ == "0.1.0-dev"


def test_get_version():
    assert get_version() == "0.1.0-dev"


def test_is_stable():
    assert is_stable() == False  # Development version
