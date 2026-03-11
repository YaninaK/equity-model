# src/equity_model/data/cleaner.py

"""Очистка и обработка данных."""

import logging
from typing import Any, Dict, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class DataCleaner:
    """Очистка данных: пропуски, дивиденды, доходности."""

    def __init__(self, config: Dict[str, Any]) -> None:
        """
        Инициализация очистителя данных.

        Args:
            config: Словарь с конфигурацией.
        """
        self.config = config
        self.liquidity_threshold = config["data"]["liquidity_threshold"]
        self.max_forward_fill = config["data"]["max_forward_fill_days"]
        logger.info(
            f"DataCleaner инициализирован. Порог ликвидности: {self.liquidity_threshold}"
        )

    def calculate_missing_pct(self, prices: pd.Series, window_days: int = 504) -> float:
        """
        Расчёт процента пропусков за последние N дней.

        Args:
            prices: Временной ряд цен.
            window_days: Размер окна для расчёта (по умолчанию 504 торговых дня ≈ 2 года).

        Returns:
            Процент пропусков от 0.0 до 1.0.
        """
        recent = prices.tail(window_days)
        missing_pct = recent.isna().sum() / len(recent)
        logger.debug(f"Процент пропусков: {missing_pct:.2%}")
        return missing_pct

    def filter_by_liquidity(
        self, df: pd.DataFrame, missing_pct: pd.Series
    ) -> Tuple[pd.DataFrame, pd.Series]:
        """
        Фильтрация инструментов по ликвидности.

        Args:
            df: DataFrame с ценами.
            missing_pct: Series с процентом пропусков для каждого инструмента.

        Returns:
            Кортеж (отфильтрованный DataFrame, статус ликвидности).
        """
        passed = missing_pct[missing_pct <= self.liquidity_threshold].index
        filtered_df = df[passed]
        status = pd.Series("Pass", index=df.columns)
        status[~df.columns.isin(passed)] = "Fail"

        n_passed = len(passed)
        n_total = len(df.columns)
        logger.info(f"Фильтрация ликвидности: {n_passed}/{n_total} инструментов прошло")

        return filtered_df, status

    def forward_fill(
        self, df: pd.DataFrame, limit: Optional[int] = None
    ) -> pd.DataFrame:
        """
        Заполнение пропусков методом forward fill.

        Args:
            df: DataFrame с ценами.
            limit: Максимальное количество последовательных пропусков для заполнения.

        Returns:
            DataFrame с заполненными пропусками.
        """
        limit = limit or self.max_forward_fill
        logger.debug(f"Forward fill с лимитом: {limit} дней")
        return df.ffill(limit=limit)

    def adjust_dividends(
        self, prices: pd.DataFrame, dividends: Optional[pd.DataFrame] = None
    ) -> pd.DataFrame:
        """
        Корректировка цен на дивиденды (если TRI недоступен).

        Args:
            prices: DataFrame с ценами.
            dividends: DataFrame с дивидендами (опционально).

        Returns:
            DataFrame с скорректированными ценами.
        """
        if dividends is None:
            logger.warning("Дивиденды не предоставлены, пропускаем корректировку")
            return prices

        try:
            adj_factor = (1 + dividends.reindex(prices.index, fill_value=0)).cumprod()
            adjusted = prices * adj_factor
            logger.info("Корректировка на дивиденды выполнена")
            return adjusted
        except Exception as e:
            logger.error(f"Ошибка корректировки дивидендов: {e}")
            return prices

    def calculate_log_returns(self, prices: pd.DataFrame) -> pd.DataFrame:
        """
        Расчёт логарифмических доходностей.

        Args:
            prices: DataFrame с ценами.

        Returns:
            DataFrame с логарифмическими доходностями.
        """
        logger.debug("Расчёт логарифмических доходностей")
        return np.log(prices / prices.shift(1))

    def create_fill_flag(
        self, original: pd.DataFrame, cleaned: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Создание флага искусственного заполнения пропусков.

        Args:
            original: DataFrame с исходными данными.
            cleaned: DataFrame с очищенными данными.

        Returns:
            DataFrame с флагами (True = заполнено искусственно).
        """
        logger.debug("Создание флагов заполнений")
        return original.isna() & cleaned.notna()
