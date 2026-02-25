# tests/unit/data/test_moex_loader.py

"""Тесты для MOEX загрузчика с моками."""

import sys
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from equity_model.data.moex_loader import DataSourceError, MOEXDataSource
from tests.mocks import MockMOEXClient


class TestMOEXDataSource:
    """Тесты для MOEXDataSource."""

    @pytest.fixture
    def config(self):
        """Фикстура с конфигурацией."""
        return {
            "data": {
                "source": "moex",
                "moex": {"exchange": "MOEX", "market": "stock", "board": "TQBR"},
            },
            "paths": {"raw_data": "data/raw", "processed_data": "data/processed"},
        }

    @pytest.fixture
    def moex_source(self, config):
        """Фикстура с MOEX источником."""
        return MOEXDataSource(config)

    @pytest.fixture
    def mock_moexalgo(self):
        """Фикстура с моком moexalgo."""
        mock = MagicMock()
        mock.trades = MockMOEXClient.trades
        mock.dividends = MockMOEXClient.dividends
        mock.get_info = MockMOEXClient.get_info
        return mock

    def test_connect_success(self, moex_source, mock_moexalgo):
        """Тест успешного подключения."""
        with patch.dict("sys.modules", {"moexalgo": mock_moexalgo}):
            result = moex_source.connect()
            assert result is True
            assert moex_source.is_connected is True

    def test_connect_import_error(self, moex_source):
        """Тест ошибки импорта moexalgo."""
        # Временно удаляем moexalgo из sys.modules
        original = sys.modules.get("moexalgo")
        try:
            if "moexalgo" in sys.modules:
                del sys.modules["moexalgo"]

            with patch.dict("sys.modules", {"moexalgo": None}, clear=False):
                with pytest.raises(DataSourceError):
                    moex_source.connect()
        finally:
            # Восстанавливаем оригинал
            if original:
                sys.modules["moexalgo"] = original

    def test_load_prices(self, moex_source, mock_moexalgo):
        """Тест загрузки цен."""
        with patch.dict("sys.modules", {"moexalgo": mock_moexalgo}):
            moex_source.connect()

            tickers = ["SBER", "GAZP"]
            result = moex_source.load_prices(tickers, "2023-01-01", "2023-12-31")

            assert isinstance(result, pd.DataFrame)
            assert "ticker" in result.columns
            assert "close" in result.columns
            assert len(result) > 0

    def test_load_prices_not_connected(self, moex_source):
        """Тест загрузки без подключения."""
        with pytest.raises(DataSourceError):
            moex_source.load_prices(["SBER"])

    def test_load_dividends(self, moex_source, mock_moexalgo):
        """Тест загрузки дивидендов."""
        with patch.dict("sys.modules", {"moexalgo": mock_moexalgo}):
            moex_source.connect()

            result = moex_source.load_dividends(["SBER"])

            assert result is None or isinstance(result, pd.DataFrame)

    def test_load_metadata(self, moex_source, mock_moexalgo):
        """Тест загрузки метаданных."""
        with patch.dict("sys.modules", {"moexalgo": mock_moexalgo}):
            moex_source.connect()

            result = moex_source.load_metadata(["SBER", "GAZP"])

            assert isinstance(result, pd.DataFrame)
            assert "ticker" in result.columns

    def test_disconnect(self, moex_source, mock_moexalgo):
        """Тест отключения."""
        with patch.dict("sys.modules", {"moexalgo": mock_moexalgo}):
            moex_source.connect()
            moex_source.disconnect()
            assert moex_source.is_connected is False

    def test_context_manager(self, moex_source, mock_moexalgo):
        """Тест контекстного менеджера."""
        with patch.dict("sys.modules", {"moexalgo": mock_moexalgo}):
            with moex_source as source:
                assert source.is_connected is True
            assert moex_source.is_connected is False
