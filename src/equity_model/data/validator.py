# src/equity_model/data/validator.py

"""Валидация данных."""

import logging
from typing import Any, Dict, List

import pandas as pd

logger = logging.getLogger(__name__)


class DataValidator:
    """Валидация качества данных."""

    def __init__(self, config: Dict[str, Any]) -> None:
        """
        Инициализация валидатора.

        Args:
            config: Словарь с конфигурацией.
        """
        self.config = config
        self.min_history = config["data"]["min_history_years"] * 247
        logger.info(
            f"DataValidator инициализирован. Минимум истории: {self.min_history} дней"
        )

    def check_history_length(self, df: pd.DataFrame) -> Dict[str, bool]:
        """
        Проверка достаточности истории для каждого инструмента.

        Args:
            df: DataFrame с ценами.

        Returns:
            Словарь {ticker: bool} с результатом проверки.
        """
        result = {col: len(df[col].dropna()) >= self.min_history for col in df.columns}
        n_passed = sum(result.values())
        logger.info(f"Проверка истории: {n_passed}/{len(result)} инструментов прошло")
        return result

    def check_no_negative_prices(self, df: pd.DataFrame) -> bool:
        """
        Проверка на отрицательные цены.

        Args:
            df: DataFrame с ценами.

        Returns:
            True если все цены неотрицательные.
        """
        result = (df >= 0).all().all()
        logger.debug(f"Проверка отрицательных цен: {'OK' if result else 'FAIL'}")
        return result

    def check_no_future_leak(
        self, train_dates: pd.DatetimeIndex, test_dates: pd.DatetimeIndex
    ) -> bool:
        """
        Проверка отсутствия утечки данных из будущего.

        Args:
            train_dates: Индекс дат обучающей выборки.
            test_dates: Индекс дат тестовой выборки.

        Returns:
            True если утечки нет.
        """
        result = train_dates.max() < test_dates.min()
        logger.debug(f"Проверка утечки данных: {'OK' if result else 'FAIL'}")
        return result

    def validate_split(self, train: pd.DataFrame, test: pd.DataFrame) -> bool:
        """
        Комплексная валидация разделения выборки.

        Args:
            train: Обучающая выборка.
            test: Тестовая выборка.

        Returns:
            True если все проверки пройдены.
        """
        checks = [
            self.check_no_future_leak(
                (
                    train.index.get_level_values("date").unique()
                    if isinstance(train.index, pd.MultiIndex)
                    else train.index
                ),
                (
                    test.index.get_level_values("date").unique()
                    if isinstance(test.index, pd.MultiIndex)
                    else test.index
                ),
            ),
            len(test) >= 335,
            len(train) >= self.min_history,
        ]
        result = all(checks)
        logger.info(f"Валидация split: {'OK' if result else 'FAIL'}")
        return result
