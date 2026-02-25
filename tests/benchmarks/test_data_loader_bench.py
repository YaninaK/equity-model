# tests/benchmarks/test_data_loader_bench.py

"""Бенчмарки производительности для модуля загрузки данных.

Используется для отслеживания регрессий производительности
и обеспечения SLA пайплайна (< 15 минут для ежедневного запуска).
"""

from datetime import datetime, timedelta
from typing import Any, Dict

import numpy as np
import pandas as pd
import pytest

from equity_model.data.cleaner import DataCleaner
from equity_model.data.loader import DataLoader
from tests.mocks import create_mock_prices, mock_moexalgo


@pytest.mark.benchmark
class TestDataLoaderBenchmarks:
    """Бенчмарки для DataLoader."""

    @pytest.fixture
    def large_dataset(self) -> pd.DataFrame:
        """Большой набор данных для тестов производительности (260 инструментов × 500 дней)."""
        tickers = [f"TICKER{i:03d}" for i in range(260)]
        return create_mock_prices(tickers, days=500)

    @pytest.fixture
    def small_dataset(self) -> pd.DataFrame:
        """Малый набор данных для быстрых тестов (10 инструментов × 100 дней)."""
        tickers = [f"TICKER{i:03d}" for i in range(10)]
        return create_mock_prices(tickers, days=100)

    @pytest.fixture
    def loader_config(self, tmp_path) -> Dict[str, Any]:
        """Конфигурация для бенчмарков."""
        return {
            "data": {
                "source": "moex",
                "liquidity_threshold": 0.20,
                "max_forward_fill_days": 5,
            },
            "paths": {
                "raw_data": str(tmp_path / "raw"),
                "processed_data": str(tmp_path / "processed"),
            },
        }

    def test_load_prices_performance_small(
        self,
        benchmark,
        small_dataset: pd.DataFrame,
        loader_config: Dict[str, Any],
        tmp_path,
    ):
        """Бенчмарк загрузки малого набора данных."""
        import yaml

        config_file = tmp_path / "config.yaml"
        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(loader_config, f)

        loader = DataLoader(str(config_file))

        # Сохраняем тестовые данные как "сырые"
        loader.save_raw(small_dataset, "benchmark_small.parquet")

        # Бенчмарк загрузки
        result = benchmark(loader.load_raw, "benchmark_small.parquet")

        assert len(result) > 0
        benchmark.extra_info["rows"] = len(result)
        benchmark.extra_info["columns"] = len(result.columns)

    def test_load_prices_performance_large(
        self,
        benchmark,
        large_dataset: pd.DataFrame,
        loader_config: Dict[str, Any],
        tmp_path,
    ):
        """Бенчмарк загрузки большого набора данных (260 инструментов)."""
        import yaml

        config_file = tmp_path / "config.yaml"
        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(loader_config, f)

        loader = DataLoader(str(config_file))
        loader.save_raw(large_dataset, "benchmark_large.parquet")

        result = benchmark(loader.load_raw, "benchmark_large.parquet")

        assert len(result) > 0
        benchmark.extra_info["rows"] = len(result)
        benchmark.extra_info["columns"] = len(result.columns)
        benchmark.extra_info["instruments"] = 260

    def test_save_raw_performance(
        self,
        benchmark,
        large_dataset: pd.DataFrame,
        loader_config: Dict[str, Any],
        tmp_path,
    ):
        """Бенчмарк сохранения сырых данных."""
        import yaml

        config_file = tmp_path / "config.yaml"
        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(loader_config, f)

        loader = DataLoader(str(config_file))

        benchmark(loader.save_raw, large_dataset, "benchmark_save.parquet")

        # Проверяем что файл создан
        assert (tmp_path / "raw" / "benchmark_save.parquet").exists()


@pytest.mark.benchmark
class TestDataCleanerBenchmarks:
    """Бенчмарки для DataCleaner."""

    @pytest.fixture
    def large_prices(self) -> pd.DataFrame:
        """Большие данные для тестов очистителя (260 инструментов × 500 дней)."""
        tickers = [f"TICKER{i:03d}" for i in range(260)]
        dates = pd.date_range("2020-01-01", periods=500, freq="B")

        data = {}
        for ticker in tickers:
            data[ticker] = np.random.randn(500).cumsum() + 100

        return pd.DataFrame(data, index=dates)

    @pytest.fixture
    def config(self) -> Dict[str, Any]:
        """Конфигурация для бенчмарков."""
        return {"data": {"liquidity_threshold": 0.20, "max_forward_fill_days": 5}}

    def test_forward_fill_performance(
        self, benchmark, large_prices: pd.DataFrame, config: Dict[str, Any]
    ):
        """Бенчмарк производительности forward fill."""
        cleaner = DataCleaner(config)

        # Добавляем пропуски для реалистичности
        prices_with_gaps = large_prices.copy()
        prices_with_gaps.iloc[::10, ::5] = np.nan

        result = benchmark(cleaner.forward_fill, prices_with_gaps)

        assert result.shape == prices_with_gaps.shape
        benchmark.extra_info["instruments"] = 260
        benchmark.extra_info["days"] = 500

    def test_calculate_log_returns_performance(
        self, benchmark, large_prices: pd.DataFrame, config: Dict[str, Any]
    ):
        """Бенчмарк расчёта логарифмических доходностей."""
        cleaner = DataCleaner(config)

        result = benchmark(cleaner.calculate_log_returns, large_prices)

        assert result.shape == large_prices.shape
        assert result.iloc[0].isna().all()  # Первый ряд NaN

    def test_filter_by_liquidity_performance(
        self, benchmark, large_prices: pd.DataFrame, config: Dict[str, Any]
    ):
        """Бенчмарк фильтрации по ликвидности."""
        cleaner = DataCleaner(config)

        # Создаём процент пропусков для каждого инструмента
        missing_pct = pd.Series(
            np.random.uniform(0, 0.3, len(large_prices.columns)),
            index=large_prices.columns,
        )

        result, status = benchmark(
            cleaner.filter_by_liquidity, large_prices, missing_pct
        )

        assert isinstance(result, pd.DataFrame)
        assert len(status) == len(large_prices.columns)
