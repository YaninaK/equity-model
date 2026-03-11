# src/equity_model/data/wrapper.py

"""Удобный доступ к витрине данных."""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

logger = logging.getLogger(__name__)


class DataMartError(Exception):
    """Исключение для ошибок DataMart."""

    pass


class DataMart:
    """Обёртка для загрузки обработанных данных."""

    def __init__(self, config_path: str = "config/base.yaml") -> None:
        """
        Инициализация DataMart.

        Args:
            config_path: Путь к файлу конфигурации.

        Raises:
            DataMartError: Если конфигурация не найдена.
        """
        try:
            import yaml

            with open(config_path, "r", encoding="utf-8") as f:
                self.config = yaml.safe_load(f)
            self.prices_path = Path(self.config["paths"]["prices"])
            self.metadata_path = Path(self.config["paths"]["metadata"])
            self.test_window = self.config["data"]["test_window_days"]
            self.wf_step = self.config["data"]["walk_forward_step"]
            self.wf_folds = self.config["data"]["walk_forward_folds"]
            logger.info(f"DataMart инициализирован. Цены: {self.prices_path}")
        except Exception as e:
            logger.error(f"Ошибка инициализации DataMart: {e}")
            raise DataMartError(f"Failed to initialize DataMart: {e}") from e

    def load_prices(self, tickers: Optional[List[str]] = None) -> pd.DataFrame:
        """
        Загрузка цен из витрины.

        Args:
            tickers: Список тикеров для загрузки (опционально).

        Returns:
            DataFrame с ценами (индекс: date, ticker).

        Raises:
            DataMartError: Если файл не найден.
        """
        try:
            logger.info(f"Загрузка цен из {self.prices_path}")
            df = pd.read_parquet(self.prices_path)
            if tickers:
                df = df[df["ticker"].isin(tickers)]
                logger.info(f"Отфильтровано {len(tickers)} тикеров")
            return df.set_index(["date", "ticker"])
        except FileNotFoundError as e:
            logger.error(f"Файл цен не найден: {self.prices_path}")
            raise DataMartError(f"Prices file not found: {self.prices_path}") from e
        except Exception as e:
            logger.error(f"Ошибка загрузки цен: {e}")
            raise DataMartError(f"Failed to load prices: {e}") from e

    def load_metadata(self) -> pd.DataFrame:
        """
        Загрузка метаданных.

        Returns:
            DataFrame с метаданными.

        Raises:
            DataMartError: Если файл не найден.
        """
        try:
            logger.info(f"Загрузка метаданных из {self.metadata_path}")
            return pd.read_csv(self.metadata_path)
        except FileNotFoundError as e:
            logger.error(f"Файл метаданных не найден: {self.metadata_path}")
            raise DataMartError(f"Metadata file not found: {self.metadata_path}") from e
        except Exception as e:
            logger.error(f"Ошибка загрузки метаданных: {e}")
            raise DataMartError(f"Failed to load metadata: {e}") from e

    def get_train_test_split(
        self, offset_days: int = 365
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Получение разделения Train/Test.

        Args:
            offset_days: Количество дней для тестовой выборки.

        Returns:
            Кортеж (train DataFrame, test DataFrame).
        """
        prices = self.load_prices()
        last_date = prices.index.get_level_values("date").max()
        train_end = last_date - pd.Timedelta(days=offset_days)

        train = prices[prices.index.get_level_values("date") <= train_end]
        test = prices[prices.index.get_level_values("date") > train_end]

        logger.info(f"Train/Test split: {len(train)} / {len(test)} записей")
        return train, test

    def get_walk_forward_folds(
        self, n_folds: Optional[int] = None, step_days: Optional[int] = None
    ) -> List[Tuple[pd.DataFrame, pd.DataFrame]]:
        """
        Генератор фолдов для Walk-Forward валидации.

        Args:
            n_folds: Количество фолдов (по умолчанию из конфига).
            step_days: Шаг в днях между фолдами (по умолчанию из конфига).

        Returns:
            Список кортежей (train DataFrame, test DataFrame) для каждого фолда.
        """
        n_folds = n_folds or self.wf_folds
        step_days = step_days or self.wf_step

        train_base, test_full = self.get_train_test_split(offset_days=self.test_window)
        test_dates = sorted(test_full.index.get_level_values("date").unique())

        folds = []
        for i in range(0, len(test_dates) - step_days, step_days):
            if len(folds) >= n_folds:
                break

            fold_start = test_dates[i]
            fold_end = (
                test_dates[i + step_days]
                if i + step_days < len(test_dates)
                else test_dates[-1]
            )

            # Обучающая выборка: вся история до начала тестового окна фолда
            train_fold = train_base[
                train_base.index.get_level_values("date") <= fold_start
            ]
            # Тестовая выборка: окно фолда
            test_fold = test_full[
                (test_full.index.get_level_values("date") >= fold_start)
                & (test_full.index.get_level_values("date") <= fold_end)
            ]

            folds.append((train_fold, test_fold))

        logger.info(f"Сгенерировано {len(folds)} фолдов для Walk-Forward")
        return folds
