# src/equity_model/data/loader.py

"""Загрузчик данных с поддержкой множественных источников."""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from .base import BaseDataSource, DataSourceError
from .factory import DataSourceFactory

logger = logging.getLogger(__name__)


class DataLoaderError(Exception):
    """Исключение для ошибок загрузчика данных."""

    pass


class DataLoader:
    """
    Загрузчик исторических данных с поддержкой переключения источников.

    Использует фабрику для создания нужного источника данных
    на основе конфигурации.
    """

    def __init__(self, config_path: str = "config/base.yaml") -> None:
        """
        Инициализация загрузчика данных.

        Args:
            config_path: Путь к файлу конфигурации YAML.

        Raises:
            DataLoaderError: Если конфигурация не найдена.
        """
        try:
            import yaml

            self.config = self._load_config(config_path)
            self.raw_path = Path(self.config["paths"]["raw_data"])
            self.raw_path.mkdir(parents=True, exist_ok=True)

            # Создание источника данных через фабрику
            self._source: Optional[BaseDataSource] = None
            logger.info(
                f"DataLoader инициализирован. Источник: {self.config['data'].get('source', 'moex')}"
            )

        except FileNotFoundError as e:
            logger.error(f"Файл конфигурации не найден: {config_path}")
            raise DataLoaderError(f"Config file not found: {config_path}") from e
        except Exception as e:
            logger.error(f"Ошибка инициализации: {e}")
            raise DataLoaderError(f"Initialization error: {e}") from e

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Загрузка конфигурации из YAML."""
        import yaml

        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def get_source(self) -> BaseDataSource:
        """
        Получение источника данных.

        Returns:
            Экземпляр источника данных.
        """
        if self._source is None:
            self._source = DataSourceFactory.create(self.config)
        return self._source

    def load_prices(
        self,
        tickers: List[str],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Загрузка цен через текущий источник данных.

        Args:
            tickers: Список тикеров.
            start_date: Начальная дата.
            end_date: Конечная дата.

        Returns:
            DataFrame с ценами.
        """
        source = self.get_source()

        with source:  # Контекстный менеджер для connect/disconnect
            return source.load_prices(tickers, start_date, end_date)

    def load_dividends(
        self,
        tickers: List[str],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Optional[pd.DataFrame]:
        """Загрузка дивидендов."""
        source = self.get_source()

        with source:
            return source.load_dividends(tickers, start_date, end_date)

    def load_metadata(self, tickers: List[str]) -> pd.DataFrame:
        """Загрузка метаданных."""
        source = self.get_source()

        with source:
            return source.load_metadata(tickers)

    def save_raw(self, data: pd.DataFrame, filename: str) -> None:
        """
        Сохранение сырых данных в Parquet формат.

        Args:
            data: DataFrame для сохранения.
            filename: Имя файла.

        Raises:
            DataLoaderError: Если сохранение не удалось.
        """
        try:
            filepath = self.raw_path / filename
            # ← ИСПРАВЛЕНО: index=True для сохранения индекса (даты)
            data.to_parquet(filepath, index=True)
            logger.info(f"Сырые данные сохранены: {filepath}")
        except Exception as e:
            logger.error(f"Ошибка сохранения: {e}")
            raise DataLoaderError(f"Failed to save raw data: {e}") from e

    def load_raw(self, filename: str) -> pd.DataFrame:
        """
        Загрузка сырых данных из Parquet файла.

        Args:
            filename: Имя файла.

        Returns:
            DataFrame с сырыми данными.

        Raises:
            DataLoaderError: Если файл не найден.
        """
        try:
            filepath = self.raw_path / filename
            logger.info(f"Загрузка сырых данных: {filepath}")
            return pd.read_parquet(filepath)
        except FileNotFoundError as e:
            raise DataLoaderError(f"Raw file not found: {filepath}") from e
        except Exception as e:
            logger.error(f"Ошибка чтения сырых данных: {e}")
            raise DataLoaderError(f"Failed to load raw data: {e}") from e
