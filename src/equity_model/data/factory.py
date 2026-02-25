# src/equity_model/data/factory.py

"""Фабрика для создания источников данных."""

import logging
from typing import Any, Dict, Type

from .base import BaseDataSource, DataSourceError

logger = logging.getLogger(__name__)


class DataSourceFactory:
    """
    Фабрика для создания источников данных.

    Позволяет переключаться между источниками через конфигурацию.
    """

    _registry: Dict[str, Type[BaseDataSource]] = {}

    @classmethod
    def register(cls, name: str, source_class: Type[BaseDataSource]) -> None:
        """
        Регистрация источника данных.

        Args:
            name: Имя источника (для конфигурации).
            source_class: Класс источника данных.
        """
        cls._registry[name] = source_class
        logger.info(f"Зарегистрирован источник данных: {name}")

    @classmethod
    def create(cls, config: Dict[str, Any]) -> BaseDataSource:
        """
        Создание источника данных на основе конфигурации.

        Args:
            config: Конфигурация проекта.

        Returns:
            Экземпляр источника данных.

        Raises:
            DataSourceError: Если источник не найден.
        """
        source_type = config.get("data", {}).get("source", "moex")

        if source_type not in cls._registry:
            available = list(cls._registry.keys())
            raise DataSourceError(
                f"Неизвестный источник данных: {source_type}. "
                f"Доступные: {available}"
            )

        source_class = cls._registry[source_type]
        logger.info(f"Создание источника данных: {source_type}")

        return source_class(config)

    @classmethod
    def get_available_sources(cls) -> list:
        """Получение списка доступных источников."""
        return list(cls._registry.keys())


# Регистрация источников при импорте модуля
def _register_default_sources() -> None:
    """Регистрация источников данных по умолчанию."""
    try:
        from .moex_loader import MOEXDataSource

        DataSourceFactory.register("moex", MOEXDataSource)
    except ImportError as e:
        logger.warning(f"MOEX источник не доступен: {e}")

    try:
        from .bank_loader import BankStorageDataSource

        DataSourceFactory.register("bank_storage", BankStorageDataSource)
    except ImportError as e:
        logger.warning(f"Bank источник не доступен: {e}")


_register_default_sources()
