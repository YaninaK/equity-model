# tests/conftest.py

"""Общие фикстуры и настройка пути для тестов."""

import sys
from pathlib import Path

# Добавляем src/ в sys.path для импорта пакета
ROOT_DIR = Path(__file__).parent.parent
SRC_DIR = ROOT_DIR / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# Теперь импорты работают:
# from equity_model.data.base import BaseDataSource


from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml


@pytest.fixture
def config():
    """Фикстура с конфигурацией."""
    return {
        "data": {
            "source": "moex",
            "liquidity_threshold": 0.20,
            "max_forward_fill_days": 5,
            "min_history_years": 2,
            "test_window_days": 365,
            "walk_forward_step": 30,
            "walk_forward_folds": 10,
            "moex": {"exchange": "MOEX", "market": "stock", "board": "TQBR"},
            "bank_storage": {
                "host": "test-db.vtb.ru",
                "port": 5432,
                "database": "test_data",
                "schema": "equity",
                "table": "daily_prices",
            },
        },
        "paths": {
            "raw_data": "data/raw",
            "processed_data": "data/processed",
            "metadata": "data/processed/metadata.csv",
            "prices": "data/processed/prices_processed.parquet",
        },
        "logging": {
            "level": "DEBUG",
            "format": "%(asctime)s - %(levelname)s - %(message)s",
        },
    }


@pytest.fixture
def sample_prices():
    """Фикстура с тестовыми ценами."""
    dates = pd.date_range("2020-01-01", periods=504, freq="B")
    data = {
        "SBER": np.random.randn(504).cumsum() + 100,
        "GAZP": np.random.randn(504).cumsum() + 50,
        "LKOH": np.random.randn(504).cumsum() + 75,
    }
    return pd.DataFrame(data, index=dates)


@pytest.fixture
def temp_config_file(tmp_path, config):
    """Фикстура с временным файлом конфигурации."""
    config_file = tmp_path / "test_config.yaml"
    with open(config_file, "w", encoding="utf-8") as f:
        yaml.dump(config, f)
    return str(config_file)


@pytest.fixture
def temp_data_dir(tmp_path):
    """Фикстура с временной директорией для данных."""
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir
