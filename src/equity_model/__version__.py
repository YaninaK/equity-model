# src/equity_model/__version__.py
"""
Информация о версии пакета Equity Model.
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
    """Получить текущую версию пакета в виде строки."""
    return __version__


def get_version_info() -> tuple:
    """Получить текущую версию пакета в виде кортежа."""
    return __version_info__


def is_stable() -> bool:
    """Проверить, является ли текущая версия стабильной.."""
    return __status__ == "stable"
