# src/equity_model/data/base.py
"""Абстрактный базовый класс для источников данных."""

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd

logger = logging.getLogger(__name__)


class DataSourceError(Exception):
    """Исключение для ошибок источника данных."""

    pass


class BaseDataSource(ABC):
    """
    Абстрактный базовый класс для всех источников данных.

    Все источники данных должны реализовывать этот интерфейс
    для обеспечения совместимости и возможности переключения.
    """

    def __init__(self, config: Dict[str, Any]) -> None:
        """
        Инициализация источника данных.

        Args:
            config: Словарь с конфигурацией источника.
        """
        self.config = config
        self._connected = False
        logger.info(f"{self.__class__.__name__} инициализирован")

    @abstractmethod
    def connect(self) -> bool:
        """
        Установление соединения с источником данных.

        Returns:
            True если соединение успешно установлено.

        Raises:
            DataSourceError: Если соединение не удалось.
        """
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """
        Закрытие соединения с источником данных.
        """
        pass

    @abstractmethod
    def load_prices(
        self,
        tickers: List[str],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Загрузка исторических цен по инструментам.

        Args:
            tickers: Список тикеров для загрузки.
            start_date: Начальная дата (YYYY-MM-DD).
            end_date: Конечная дата (YYYY-MM-DD).

        Returns:
            DataFrame с колонками: date, ticker, open, high, low, close, volume.

        Raises:
            DataSourceError: Если загрузка не удалась.
        """
        pass

    @abstractmethod
    def load_dividends(
        self,
        tickers: List[str],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Optional[pd.DataFrame]:
        """
        Загрузка данных по дивидендам.

        Args:
            tickers: Список тикеров для загрузки.
            start_date: Начальная дата (YYYY-MM-DD).
            end_date: Конечная дата (YYYY-MM-DD).

        Returns:
            DataFrame с дивидендами или None если недоступно.
        """
        pass

    @abstractmethod
    def load_metadata(self, tickers: List[str]) -> pd.DataFrame:
        """
        Загрузка метаданных по инструментам.

        Args:
            tickers: Список тикеров для загрузки.

        Returns:
            DataFrame с метаданными (sector, listing_date, currency, etc.).
        """
        pass

    @property
    def is_connected(self) -> bool:
        """Проверка статуса соединения."""
        return self._connected

    def __enter__(self) -> "BaseDataSource":
        """Контекстный менеджер для подключения."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Контекстный менеджер для отключения."""
        self.disconnect()
