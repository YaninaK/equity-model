# tests/unit/data/test_validator.py

"""Тесты для модуля валидации."""

import pandas as pd
import pytest

from src.equity_model.data.validator import DataValidator


@pytest.fixture
def config():
    return {"data": {"min_history_years": 2}}


@pytest.fixture
def validator(config):
    return DataValidator(config)


def test_check_no_future_leak(validator):
    """Тест на отсутствие утечки из будущего."""
    train_dates = pd.date_range("2020-01-01", "2022-12-31")
    test_dates = pd.date_range("2023-01-01", "2023-12-31")
    assert validator.check_no_future_leak(train_dates, test_dates)


def test_check_no_negative_prices(validator):
    """Тест на отрицательные цены."""
    df = pd.DataFrame({"A": [100, 101, 102], "B": [50, 51, 52]})
    assert validator.check_no_negative_prices(df)
