# tests/unit/data/test_loader.py

"""Тесты для DataLoader (единый интерфейс)."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from equity_model.data.loader import DataLoader
from tests.mocks import MockMOEXClient


class TestDataLoader:
    """Тесты для DataLoader."""

    @pytest.fixture
    def loader(self, temp_config_file):
        """Фикстура с DataLoader."""
        return DataLoader(temp_config_file)

    @pytest.fixture
    def mock_moexalgo(self):
        """Фикстура с моком moexalgo."""
        mock = MagicMock()
        mock.trades = MockMOEXClient.trades
        mock.dividends = MockMOEXClient.dividends
        mock.get_info = MockMOEXClient.get_info
        return mock

    def test_init_success(self, loader):
        """Тест успешной инициализации."""
        assert loader._source is None  # Источник создаётся лениво

    def test_get_source_creates_instance(self, loader, mock_moexalgo):
        """Тест что get_source создаёт источник."""
        with patch.dict("sys.modules", {"moexalgo": mock_moexalgo}):
            source = loader.get_source()
            assert source is not None
            assert loader._source is source

    def test_load_prices_delegates_to_source(self, loader, mock_moexalgo):
        """Тест что load_prices делегирует источнику."""
        with patch.dict("sys.modules", {"moexalgo": mock_moexalgo}):
            tickers = ["SBER", "GAZP"]
            result = loader.load_prices(tickers, "2023-01-01", "2023-12-31")

            assert isinstance(result, pd.DataFrame)
            assert "ticker" in result.columns

    def test_load_dividends_delegates_to_source(self, loader, mock_moexalgo):
        """Тест что load_dividends делегирует источнику."""
        with patch.dict("sys.modules", {"moexalgo": mock_moexalgo}):
            result = loader.load_dividends(["SBER"])
            assert result is None or isinstance(result, pd.DataFrame)

    def test_load_metadata_delegates_to_source(self, loader, mock_moexalgo):
        """Тест что load_metadata делегирует источнику."""
        with patch.dict("sys.modules", {"moexalgo": mock_moexalgo}):
            result = loader.load_metadata(["SBER", "GAZP"])
            assert isinstance(result, pd.DataFrame)
            assert "ticker" in result.columns

    def test_save_and_load_raw_csv(self, loader, temp_data_dir, sample_prices):
        """Тест сохранения и загрузки сырых данных (CSV)."""
        # Устанавливаем путь к временной директории
        loader.raw_path = Path(temp_data_dir)

        # Сохраняем в CSV
        filename = "test.csv"
        filepath = loader.raw_path / filename
        sample_prices.to_csv(filepath, index=True)

        # Загружаем обратно
        loaded = pd.read_csv(filepath, index_col=0, parse_dates=True)

        # Проверяем что данные совпадают (без проверки типа индекса и frequency)
        pd.testing.assert_frame_equal(
            sample_prices,
            loaded,
            check_exact=False,
            rtol=1e-5,
            check_index_type=False,  # Не проверяем тип индекса
            check_freq=False,  # Не проверяем frequency
        )

    def test_save_and_load_raw_parquet(self, loader, temp_data_dir, sample_prices):
        """Тест сохранения и загрузки сырых данных (Parquet)."""
        # Пропускаем если pyarrow не установлен
        pyarrow = pytest.importorskip("pyarrow")

        # Устанавливаем путь к временной директории
        loader.raw_path = Path(temp_data_dir)

        # Сохраняем в Parquet (с индексом!)
        filename = "test.parquet"
        filepath = loader.raw_path / filename
        sample_prices.to_parquet(filepath, index=True)

        # Загружаем обратно
        loaded = pd.read_parquet(filepath)

        # Проверяем что данные совпадают
        pd.testing.assert_frame_equal(
            sample_prices,
            loaded,
            check_exact=False,
            rtol=1e-5,
            check_index_type=False,  # Не проверяем тип индекса
            check_freq=False,  # Не проверяем frequency
        )

    def test_save_and_load_raw_via_methods(self, loader, temp_data_dir, sample_prices):
        """Тест сохранения и загрузки через методы DataLoader."""
        pyarrow = pytest.importorskip("pyarrow")

        loader.raw_path = Path(temp_data_dir)

        # Используем методы DataLoader
        loader.save_raw(sample_prices, "test_methods.parquet")
        loaded = loader.load_raw("test_methods.parquet")

        # Проверяем что данные совпадают
        pd.testing.assert_frame_equal(
            sample_prices,
            loaded,
            check_exact=False,
            rtol=1e-5,
            check_index_type=False,  # Не проверяем тип индекса (BusinessDay vs None)
            check_freq=False,  # Не проверяем frequency
        )
