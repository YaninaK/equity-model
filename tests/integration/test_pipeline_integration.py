"""Интеграционные тесты полного пайплайна обработки данных.

Эти тесты требуют реального подключения к внешним API (MOEX или хранилище банка).
Не запускаются по умолчанию в CI/CD — используйте маркер -m integration.

Примеры запуска:
    # Только unit-тесты (без интеграции)
    uv run pytest tests/ -v -m "not integration"

    # Только интеграционные тесты
    uv run pytest tests/integration/ -v -m integration

    # Конкретный тест с MOEX
    uv run pytest tests/integration/ -v -m moex
"""

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Tuple
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from equity_model.data.cleaner import DataCleaner
from equity_model.data.loader import DataLoader, DataLoaderError
from equity_model.data.validator import DataValidator
from equity_model.data.wrapper import DataMart, DataMartError
from tests.mocks import MockMOEXClient

# ← УБРАНО: pytest.mark.timeout (требует установки pytest-timeout)
# Оставляем только маркер integration
pytestmark = [pytest.mark.integration]


@pytest.mark.moex
class TestPipelineMOEXIntegration:
    """
    Интеграционные тесты пайплайна с MOEX.

    Все тесты помечены @pytest.mark.skip по умолчанию,
    так как требуют реального подключения к API MOEX.
    """

    @pytest.fixture
    def integration_config(self, tmp_path: Path) -> Dict[str, Any]:
        """Конфигурация для интеграционных тестов."""
        return {
            "data": {
                "source": "moex",
                "liquidity_threshold": 0.20,
                "max_forward_fill_days": 5,
                "min_history_years": 1,
                "test_window_days": 30,
                "walk_forward_step": 5,
                "walk_forward_folds": 3,
                "moex": {"exchange": "MOEX", "market": "stock", "board": "TQBR"},
            },
            "paths": {
                "raw_data": str(tmp_path / "raw"),
                "processed_data": str(tmp_path / "processed"),
                "metadata": str(tmp_path / "processed" / "metadata.csv"),
                "prices": str(tmp_path / "processed" / "prices.parquet"),
            },
            "logging": {
                "level": "INFO",
                "format": "%(asctime)s - %(levelname)s - %(message)s",
            },
        }

    @pytest.fixture
    def test_tickers(self) -> List[str]:
        """Список тикеров для тестирования (минимум для скорости)."""
        return ["SBER", "GAZP"]

    @pytest.mark.skip(
        reason="Требует подключения к MOEX API. Запускать вручную при необходимости."
    )
    def test_full_pipeline_moex(
        self,
        integration_config: Dict[str, Any],
        test_tickers: List[str],
        tmp_path: Path,
    ):
        """
        Тест полного пайплайна с загрузкой данных из MOEX.

        Проверяет:
        - Загрузка данных работает
        - Очистка данных работает
        - Валидация проходит
        - Сохранение в витрину работает
        - DataMart может загрузить сохранённые данные

        Skip по умолчанию — требует реального подключения к MOEX.
        """
        import yaml

        # Создаём директорию
        Path(integration_config["paths"]["processed_data"]).mkdir(
            parents=True, exist_ok=True
        )

        # Сохраняем конфиг
        config_file = tmp_path / "config.yaml"
        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(integration_config, f)

        # 1. Загрузка данных
        loader = DataLoader(str(config_file))
        raw_data = loader.load_prices(
            test_tickers, start_date="2023-01-01", end_date="2023-12-31"
        )

        assert isinstance(raw_data, pd.DataFrame)
        assert len(raw_data) > 0
        assert "ticker" in raw_data.columns
        assert "close" in raw_data.columns

        # 2. Очистка данных
        cleaner = DataCleaner(integration_config)

        # Преобразование в широкий формат для cleaner
        close_prices = raw_data.pivot(index="date", columns="ticker", values="close")

        missing_pct = close_prices.apply(lambda x: cleaner.calculate_missing_pct(x))
        filtered_prices, liquidity_status = cleaner.filter_by_liquidity(
            close_prices, missing_pct
        )
        cleaned_prices = cleaner.forward_fill(filtered_prices)
        log_returns = cleaner.calculate_log_returns(cleaned_prices)

        assert len(cleaned_prices) > 0
        assert not cleaned_prices.isna().all().all()

        # 3. Валидация
        validator = DataValidator(integration_config)
        history_check = validator.check_history_length(cleaned_prices)

        assert sum(history_check.values()) > 0

        # 4. Сохранение витрины (длинный формат)
        prices_long = cleaned_prices.stack().reset_index()
        prices_long.columns = ["date", "ticker", "close_adj"]

        returns_long = log_returns.stack().reset_index()
        returns_long.columns = ["date", "ticker", "log_return"]

        prices_long = prices_long.merge(returns_long, on=["date", "ticker"], how="left")
        prices_long["is_filled_flag"] = False

        prices_long.to_parquet(integration_config["paths"]["prices"], index=False)

        # 5. Сохранение метаданных
        metadata = pd.DataFrame(
            {
                "ticker": close_prices.columns,
                "liquidity_status": liquidity_status.values,
                "missing_pct": missing_pct.values,
            }
        )
        metadata.to_csv(integration_config["paths"]["metadata"], index=False)

        # 6. Проверка DataMart
        mart = DataMart(str(config_file))
        loaded_prices = mart.load_prices()

        assert len(loaded_prices) > 0
        assert "close_adj" in loaded_prices.columns
        assert "log_return" in loaded_prices.columns

    @pytest.mark.skip(
        reason="Требует подключения к MOEX API. Запускать вручную при необходимости."
    )
    def test_walk_forward_folds_moex(
        self,
        integration_config: Dict[str, Any],
        test_tickers: List[str],
        tmp_path: Path,
    ):
        """
        Тест генерации Walk-Forward фолдов с реальными данными.

        Skip по умолчанию — требует реального подключения к MOEX.
        """
        import yaml

        # Сначала запускаем полный пайплайн для создания данных
        Path(integration_config["paths"]["processed_data"]).mkdir(
            parents=True, exist_ok=True
        )

        config_file = tmp_path / "config.yaml"
        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(integration_config, f)

        loader = DataLoader(str(config_file))
        raw_data = loader.load_prices(
            test_tickers, start_date="2023-01-01", end_date="2023-12-31"
        )

        cleaner = DataCleaner(integration_config)
        close_prices = raw_data.pivot(index="date", columns="ticker", values="close")
        cleaned_prices = cleaner.forward_fill(close_prices)
        log_returns = cleaner.calculate_log_returns(cleaned_prices)

        # Сохранение
        prices_long = cleaned_prices.stack().reset_index()
        prices_long.columns = ["date", "ticker", "close_adj"]

        returns_long = log_returns.stack().reset_index()
        returns_long.columns = ["date", "ticker", "log_return"]

        prices_long = prices_long.merge(returns_long, on=["date", "ticker"], how="left")
        prices_long["is_filled_flag"] = False
        prices_long.to_parquet(integration_config["paths"]["prices"], index=False)

        metadata = pd.DataFrame(
            {
                "ticker": close_prices.columns,
                "liquidity_status": ["Pass"] * len(close_prices.columns),
                "missing_pct": [0.0] * len(close_prices.columns),
            }
        )
        metadata.to_csv(integration_config["paths"]["metadata"], index=False)

        # Тест Walk-Forward
        mart = DataMart(str(config_file))
        folds = mart.get_walk_forward_folds(n_folds=3, step_days=5)

        assert len(folds) > 0

        for i, (train, test) in enumerate(folds):
            assert len(train) > 0, f"Fold {i}: train пустой"
            assert len(test) > 0, f"Fold {i}: test пустой"

            # Проверка отсутствия утечки данных
            train_max = train.index.get_level_values("date").max()
            test_min = test.index.get_level_values("date").min()
            assert train_max <= test_min, f"Fold {i}: утечка данных!"


@pytest.mark.bank
class TestPipelineBankIntegration:
    """
    Интеграционные тесты пайплайна с хранилищем банка.

    Все тесты помечены @pytest.mark.skip по умолчанию,
    так как требуют доступа к внутренней инфраструктуре банка.
    """

    @pytest.fixture
    def bank_config(self, tmp_path: Path) -> Dict[str, Any]:
        """Конфигурация для тестов с хранилищем банка."""
        return {
            "data": {
                "source": "bank_storage",
                "liquidity_threshold": 0.20,
                "max_forward_fill_days": 5,
                "min_history_years": 1,
                "test_window_days": 30,
                "walk_forward_step": 5,
                "walk_forward_folds": 3,
                "bank_storage": {
                    "host": "internal-db.vtb.ru",
                    "port": 5432,
                    "database": "market_data",
                    "schema": "equity",
                    "table": "daily_prices",
                    "auth_method": "kerberos",
                },
            },
            "paths": {
                "raw_data": str(tmp_path / "raw"),
                "processed_data": str(tmp_path / "processed"),
                "metadata": str(tmp_path / "processed" / "metadata.csv"),
                "prices": str(tmp_path / "processed" / "prices.parquet"),
            },
        }

    @pytest.mark.skip(
        reason="Требует доступа к хранилищу банка. Запускать вручную при необходимости."
    )
    def test_full_pipeline_bank(self, bank_config: Dict[str, Any], tmp_path: Path):
        """
        Тест полного пайплайна с хранилищем банка.

        Skip по умолчанию — требует доступа к внутренней инфраструктуре.
        """
        import yaml

        Path(bank_config["paths"]["processed_data"]).mkdir(parents=True, exist_ok=True)

        config_file = tmp_path / "config.yaml"
        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(bank_config, f)

        loader = DataLoader(str(config_file))

        # Тест подключения
        source = loader.get_source()
        assert source.connect() is True

        # Тест загрузки данных
        tickers = ["SBER", "GAZP"]
        raw_data = loader.load_prices(
            tickers, start_date="2023-01-01", end_date="2023-12-31"
        )

        assert isinstance(raw_data, pd.DataFrame)
        assert len(raw_data) > 0

        source.disconnect()


@pytest.mark.integration
class TestPipelineErrorHandling:
    """
    Тесты обработки ошибок в интеграционном режиме.

    Эти тесты НЕ требуют подключения к внешним API и могут запускаться в CI/CD.
    """

    def test_invalid_source_config(self, tmp_path: Path):
        """Тест конфигурации с неверным источником данных."""
        import yaml

        from equity_model.data.factory import DataSourceError, DataSourceFactory

        config = {
            "data": {"source": "invalid_source"},
            "paths": {"raw_data": str(tmp_path / "raw")},
        }

        config_file = tmp_path / "config.yaml"
        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(config, f)

        with pytest.raises(DataSourceError):
            loader = DataLoader(str(config_file))
            loader.get_source()

    def test_empty_ticker_list(self, temp_config_file: str):
        """Тест загрузки с пустым списком тикеров."""
        loader = DataLoader(temp_config_file)

        # ← ИСПРАВЛЕНО: Используем patch.dict для ленивого импорта
        mock_moexalgo = MagicMock()
        mock_moexalgo.trades = MockMOEXClient.trades
        mock_moexalgo.dividends = MockMOEXClient.dividends
        mock_moexalgo.get_info = MockMOEXClient.get_info

        with patch.dict("sys.modules", {"moexalgo": mock_moexalgo}):
            result = loader.load_prices([])

            assert isinstance(result, pd.DataFrame)
            assert len(result) == 0
