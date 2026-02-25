# tests/unit/data/test_cleaner.py

"""Тесты для модуля очистки данных."""

import numpy as np
import pandas as pd
import pytest

from src.equity_model.data.cleaner import DataCleaner


@pytest.fixture
def config():
    return {
        "data": {"liquidity_threshold": 0.20, "max_forward_fill_days": 5},
        "paths": {},
    }


@pytest.fixture
def cleaner(config):
    return DataCleaner(config)


@pytest.fixture
def sample_prices():
    dates = pd.date_range("2020-01-01", periods=100, freq="D")
    data = {"TICKER1": np.random.randn(100).cumsum() + 100}
    return pd.DataFrame(data, index=dates)


def test_calculate_missing_pct(cleaner, sample_prices):
    """Тест расчёта процента пропусков."""
    sample_prices.iloc[10:15, 0] = np.nan  # 5 пропусков из 100
    pct = cleaner.calculate_missing_pct(sample_prices["TICKER1"])
    assert 0.0 <= pct <= 1.0


def test_forward_fill(cleaner, sample_prices):
    """Тест forward fill."""
    sample_prices.iloc[10:15, 0] = np.nan
    filled = cleaner.forward_fill(sample_prices)
    assert not filled.iloc[11:15, 0].isna().all()


def test_calculate_log_returns(cleaner, sample_prices):
    """Тест расчёта логарифмических доходностей."""
    returns = cleaner.calculate_log_returns(sample_prices)
    assert len(returns) == len(sample_prices)
    assert returns.iloc[0].isna().all()  # Первый элемент NaN


def test_liquidity_filter(cleaner, sample_prices):
    """Тест фильтрации по ликвидности."""
    missing_pct = pd.Series({"TICKER1": 0.10})  # 10% пропусков
    filtered, status = cleaner.filter_by_liquidity(sample_prices, missing_pct)
    assert status["TICKER1"] == "Pass"
