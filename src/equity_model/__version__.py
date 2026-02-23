# src/equity_model/__version__.py
"""
Version information for Equity Model package.
"""

__version__ = "0.1.0-dev"
__version_info__ = (0, 1, 0, "dev")

__author__ = "Yanina Kutovaya"
__author_email__ = "kutovaiayp@yandex.ru"
__description__ = "Monte Carlo Simulation for Equity Pricing"
__url__ = "https://github.com/YaninaK/equity-model"
__license__ = "MIT"
__status__ = "development"
__python_requires__ = ">=3.11"


def get_version() -> str:
    """Get the current package version as a string."""
    return __version__


def get_version_info() -> tuple:
    """Get the current package version as a tuple."""
    return __version_info__


def is_stable() -> bool:
    """Check if the current version is stable (production ready)."""
    return __status__ == "stable"
