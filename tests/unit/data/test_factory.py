# tests/unit/data/test_factory.py

"""Тесты для фабрики источников данных."""

from unittest.mock import MagicMock, patch

import pytest

from equity_model.data.base import BaseDataSource, DataSourceError
from equity_model.data.factory import DataSourceFactory


class TestDataSourceFactory:
    """Тесты для DataSourceFactory."""

    def test_get_available_sources(self):
        """Тест получения доступных источников."""
        sources = DataSourceFactory.get_available_sources()
        assert isinstance(sources, list)
        # Хотя бы один источник должен быть зарегистрирован
        assert len(sources) > 0

    def test_create_moex_source(self):
        """Тест создания MOEX источника."""
        config = {
            "data": {"source": "moex", "moex": {"exchange": "MOEX", "board": "TQBR"}},
            "paths": {"raw_data": "data/raw", "processed_data": "data/processed"},
        }

        # Патчим sys.modules чтобы предотвратить реальный импорт moexalgo
        mock_moexalgo = MagicMock()

        with patch.dict("sys.modules", {"moexalgo": mock_moexalgo}):
            result = DataSourceFactory.create(config)

            # Проверяем что создан правильный тип
            from equity_model.data.moex_loader import MOEXDataSource

            assert isinstance(result, MOEXDataSource)
            assert result._connected is False  # Ещё не подключён

    def test_create_bank_source(self):
        """Тест создания источника банка."""
        config = {
            "data": {
                "source": "bank_storage",
                "bank_storage": {
                    "host": "test-db.vtb.ru",
                    "port": 5432,
                    "database": "test_data",
                },
            },
            "paths": {"raw_data": "data/raw", "processed_data": "data/processed"},
        }

        result = DataSourceFactory.create(config)

        from equity_model.data.bank_loader import BankStorageDataSource

        assert isinstance(result, BankStorageDataSource)

    def test_create_unknown_source(self):
        """Тест создания неизвестного источника."""
        config = {"data": {"source": "unknown_source"}}

        with pytest.raises(DataSourceError) as exc_info:
            DataSourceFactory.create(config)

        assert "unknown_source" in str(exc_info.value)

    def test_register_custom_source(self):
        """Тест регистрации кастомного источника."""

        class CustomSource(BaseDataSource):
            def connect(self):
                return True

            def disconnect(self):
                pass

            def load_prices(self, tickers, start_date=None, end_date=None):
                pass

            def load_dividends(self, tickers, start_date=None, end_date=None):
                pass

            def load_metadata(self, tickers):
                pass

        # Сохраняем состояние до регистрации
        sources_before = DataSourceFactory.get_available_sources().copy()

        DataSourceFactory.register("custom", CustomSource)
        sources_after = DataSourceFactory.get_available_sources()

        assert "custom" in sources_after
        assert len(sources_after) == len(sources_before) + 1

        # Очищаем регистрацию для других тестов
        if "custom" in DataSourceFactory._registry:
            del DataSourceFactory._registry["custom"]

    def test_create_with_mock_registry(self):
        """Тест создания источника с моком в реестре."""
        config = {"data": {"source": "moex"}}

        # Создаём мок класса источника
        mock_source_class = MagicMock()
        mock_instance = MagicMock()
        mock_source_class.return_value = mock_instance

        # Патчим реестр фабрики напрямую
        original_registry = DataSourceFactory._registry.copy()
        try:
            DataSourceFactory._registry["moex"] = mock_source_class

            result = DataSourceFactory.create(config)

            assert mock_source_class.called
            assert result is mock_instance
        finally:
            # Восстанавливаем оригинальный реестр
            DataSourceFactory._registry = original_registry
