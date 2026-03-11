# tests/benchmarks/test_cleaner_bench.py

"""Бенчмарки производительности для модуля очистки данных."""

import numpy as np
import pandas as pd
import pytest

from equity_model.data.cleaner import DataCleaner


@pytest.fixture
def large_prices():
    """Большие данные для тестов производительности."""
    dates = pd.date_range("2020-01-01", periods=5000, freq="B")
    tickers = [f"TICKER{i}" for i in range(100)]

    data = {}
    for ticker in tickers:
        data[ticker] = np.random.randn(5000).cumsum() + 100

    return pd.DataFrame(data, index=dates)


@pytest.fixture
def cleaner_config():
    """Полная конфигурация для DataCleaner."""
    return {
        "data": {
            "liquidity_threshold": 0.20,
            "max_forward_fill_days": 5,
            "min_history_years": 2,
            "test_window_days": 365,
            "walk_forward_step": 30,
            "walk_forward_folds": 10,
        }
    }


def test_forward_fill_performance(benchmark, large_prices, cleaner_config):
    """Бенчмарк производительности forward fill."""
    cleaner = DataCleaner(cleaner_config)

    # Добавляем пропуски для реалистичности
    prices_with_gaps = large_prices.copy()
    prices_with_gaps.iloc[::10, ::5] = np.nan

    result = benchmark(cleaner.forward_fill, prices_with_gaps)

    assert result.shape == prices_with_gaps.shape

    # Дополнительная информация в отчёте
    benchmark.extra_info["instruments"] = 100
    benchmark.extra_info["days"] = 5000
    benchmark.extra_info["total_cells"] = prices_with_gaps.size
    benchmark.extra_info["missing_pct"] = (
        prices_with_gaps.isna().sum() / prices_with_gaps.size
    ).mean()


def test_forward_fill_performance_fallback(large_prices, cleaner_config):
    """Тест производительности без pytest-benchmark (резервный)."""
    import time

    cleaner = DataCleaner(cleaner_config)

    prices_with_gaps = large_prices.copy()
    prices_with_gaps.iloc[::10, ::5] = np.nan

    # Замер времени вручную
    start = time.perf_counter()
    result = cleaner.forward_fill(prices_with_gaps)
    elapsed = time.perf_counter() - start

    assert result.shape == prices_with_gaps.shape

    # Вывод времени в лог
    print(f"\n⏱ Forward fill: {elapsed*1000:.2f}ms для {prices_with_gaps.size} ячеек")

    # Проверка что не слишком медленно (> 5 секунд — плохо)
    assert elapsed < 5.0, f"Слишком медленно: {elapsed:.2f}s"


def test_calculate_log_returns_performance(benchmark, large_prices, cleaner_config):
    """Бенчмарк расчёта логарифмических доходностей."""
    import warnings

    cleaner = DataCleaner(cleaner_config)

    # Подавляем предупреждение о NaN (ожидаемое поведение)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        result = benchmark(cleaner.calculate_log_returns, large_prices)

    assert result.shape == large_prices.shape
    assert result.iloc[0].isna().all()  # Первый ряд NaN — это нормально

    benchmark.extra_info["instruments"] = 100
    benchmark.extra_info["days"] = 5000


def test_filter_by_liquidity_performance(benchmark, large_prices, cleaner_config):
    """Бенчмарк фильтрации по ликвидности."""
    cleaner = DataCleaner(cleaner_config)

    # Создаём процент пропусков для каждого инструмента
    missing_pct = pd.Series(
        np.random.uniform(0, 0.3, len(large_prices.columns)), index=large_prices.columns
    )

    result, status = benchmark(cleaner.filter_by_liquidity, large_prices, missing_pct)

    assert isinstance(result, pd.DataFrame)
    assert len(status) == len(large_prices.columns)

    benchmark.extra_info["instruments"] = 100
    benchmark.extra_info["threshold"] = cleaner_config["data"]["liquidity_threshold"]
