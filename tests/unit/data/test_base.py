# tests/unit/data/test_base.py

"""Тесты для абстрактного базового класса BaseDataSource."""

import sys
from abc import ABC
from unittest.mock import MagicMock, patch

import pytest

from equity_model.data.base import BaseDataSource


class TestBaseDataSource:
    """Тесты для BaseDataSource."""

    def test_is_abstract(self):
        """Тест что класс абстрактный."""
        assert issubclass(BaseDataSource, ABC)

    def test_cannot_instantiate(self):
        """Тест что нельзя создать экземпляр абстрактного класса."""
        with pytest.raises(TypeError):
            BaseDataSource({})

    def test_concrete_implementation_required(self):
        """Тест что требуются все абстрактные методы."""

        class IncompleteSource(BaseDataSource):
            def connect(self):
                return True

            # Отсутствуют остальные методы

        with pytest.raises(TypeError):
            IncompleteSource({})

    def test_context_manager_protocol(self, config):
        """Тест протокола контекстного менеджера."""
        from equity_model.data.moex_loader import MOEXDataSource

        mock_moexalgo = MagicMock()
        with patch.dict("sys.modules", {"moexalgo": mock_moexalgo}):
            source = MOEXDataSource(config)
            assert hasattr(source, "__enter__")
            assert hasattr(source, "__exit__")

    def test_is_connected_property(self, config):
        """Тест свойства is_connected."""
        from equity_model.data.moex_loader import MOEXDataSource

        mock_moexalgo = MagicMock()
        with patch.dict("sys.modules", {"moexalgo": mock_moexalgo}):
            source = MOEXDataSource(config)
            assert source.is_connected is False

            source.connect()
            assert source.is_connected is True

            source.disconnect()
            assert source.is_connected is False
