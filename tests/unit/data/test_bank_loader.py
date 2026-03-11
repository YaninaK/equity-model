# tests/unit/data/test_bank_loader.py

"""Тесты для загрузчика хранилища банка с моками."""

import pandas as pd
import pytest

from equity_model.data.bank_loader import BankStorageDataSource, DataSourceError


class TestBankStorageDataSource:
    """Тесты для BankStorageDataSource."""

    @pytest.fixture
    def config(self):
        """Фикстура с конфигурацией."""
        return {
            "data": {
                "source": "bank_storage",
                "bank_storage": {
                    "host": "test-db.vtb.ru",
                    "port": 5432,
                    "database": "test_data",
                    "schema": "equity",
                    "table": "daily_prices",
                },
            },
            "paths": {"raw_data": "data/raw", "processed_data": "data/processed"},
        }

    @pytest.fixture
    def bank_source(self, config):
        """Фикстура с источником банка."""
        return BankStorageDataSource(config)

    def test_connect_success(self, bank_source):
        """Тест успешного подключения."""
        result = bank_source.connect()
        assert result is True
        assert bank_source.is_connected is True

    def test_load_prices(self, bank_source):
        """Тест загрузки цен."""
        bank_source.connect()

        tickers = ["SBER", "GAZP"]
        result = bank_source.load_prices(tickers, "2023-01-01", "2023-12-31")

        assert isinstance(result, pd.DataFrame)
        assert "ticker" in result.columns
        assert len(result) > 0

    def test_load_prices_not_connected(self, bank_source):
        """Тест загрузки без подключения."""
        with pytest.raises(DataSourceError):
            bank_source.load_prices(["SBER"])

    def test_disconnect(self, bank_source):
        """Тест отключения."""
        bank_source.connect()
        bank_source.disconnect()
        assert bank_source.is_connected is False
