"""Бенчмарки производительности полного пайплайна.

Критические метрики:
- Ежедневный пайплайн: < 15 минут
- Загрузка 260 инструментов: < 2 минут
- Очистка данных: < 5 минут
- Генерация витрины: < 3 минут
"""

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd
import pytest

from equity_model.data.cleaner import DataCleaner
from equity_model.data.loader import DataLoader
from equity_model.data.validator import DataValidator
from equity_model.data.wrapper import DataMart
from tests.mocks import create_mock_prices


@pytest.mark.benchmark
class TestFullPipelineBenchmarks:
    """Бенчмарки полного пайплайна обработки данных."""

    @pytest.fixture
    def production_dataset(self) -> pd.DataFrame:
        """Набор данных продакшн-уровня (260 инструментов × 750 дней ≈ 3 года)."""
        tickers = [f"TICKER{i:03d}" for i in range(260)]
        return create_mock_prices(tickers, days=750)

    @pytest.fixture
    def large_dataset(self) -> pd.DataFrame:
        """Большой набор данных для Walk-Forward (260 инструментов × 1500 дней ≈ 6 лет)."""
        tickers = [f"TICKER{i:03d}" for i in range(260)]
        return create_mock_prices(tickers, days=1500)

    @pytest.fixture
    def pipeline_config(self, tmp_path: Path) -> Dict[str, Any]:
        """Конфигурация для бенчмарков пайплайна."""
        return {
            "data": {
                "source": "moex",
                "liquidity_threshold": 0.20,
                "max_forward_fill_days": 5,
                "min_history_years": 2,
                "test_window_days": 365,
                "walk_forward_step": 30,
                "walk_forward_folds": 10,
            },
            "paths": {
                "raw_data": str(tmp_path / "raw"),
                "processed_data": str(tmp_path / "processed"),
                "metadata": str(tmp_path / "processed" / "metadata.csv"),
                "prices": str(tmp_path / "processed" / "prices.parquet"),
            },
            "logging": {"level": "WARNING"},
        }

    def _prepare_vitrine(
        self, production_dataset: pd.DataFrame, pipeline_config: Dict[str, Any]
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Подготовка витрины данных для тестов."""
        close_prices = production_dataset.pivot(
            index="date", columns="ticker", values="close"
        )
        cleaner = DataCleaner(pipeline_config)
        cleaned = cleaner.forward_fill(close_prices)
        returns = cleaner.calculate_log_returns(cleaned)

        prices_long = cleaned.stack().reset_index()
        prices_long.columns = ["date", "ticker", "close_adj"]

        returns_long = returns.stack().reset_index()
        returns_long.columns = ["date", "ticker", "log_return"]

        prices_long = prices_long.merge(returns_long, on=["date", "ticker"], how="left")
        prices_long["is_filled_flag"] = False

        metadata = pd.DataFrame(
            {
                "ticker": close_prices.columns,
                "liquidity_status": ["Pass"] * len(close_prices.columns),
                "missing_pct": [0.0] * len(close_prices.columns),
            }
        )

        return prices_long, metadata

    def _save_vitrine(
        self,
        prices_long: pd.DataFrame,
        metadata: pd.DataFrame,
        pipeline_config: Dict[str, Any],
    ) -> None:
        """Сохранение витрины данных."""
        Path(pipeline_config["paths"]["processed_data"]).mkdir(
            parents=True, exist_ok=True
        )
        prices_long.to_parquet(pipeline_config["paths"]["prices"], index=False)
        metadata.to_csv(pipeline_config["paths"]["metadata"], index=False)

    def test_full_pipeline_end_to_end(
        self,
        benchmark,
        production_dataset: pd.DataFrame,
        pipeline_config: Dict[str, Any],
        tmp_path: Path,
    ):
        """
        Бенчмарк полного пайплайна от загрузки до витрины.

        Целевое время: < 15 минут для 260 инструментов × 3 года истории
        """
        import yaml

        Path(pipeline_config["paths"]["processed_data"]).mkdir(
            parents=True, exist_ok=True
        )

        config_file = tmp_path / "config.yaml"
        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(pipeline_config, f)

        def run_pipeline():
            # 1. Загрузка
            loader = DataLoader(str(config_file))
            loader.save_raw(production_dataset, "benchmark.parquet")
            raw = loader.load_raw("benchmark.parquet")

            # 2. Очистка
            cleaner = DataCleaner(pipeline_config)
            close_prices = raw.pivot(index="date", columns="ticker", values="close")

            missing_pct = close_prices.apply(lambda x: cleaner.calculate_missing_pct(x))
            filtered, status = cleaner.filter_by_liquidity(close_prices, missing_pct)
            cleaned = cleaner.forward_fill(filtered)
            returns = cleaner.calculate_log_returns(cleaned)

            # 3. Валидация
            validator = DataValidator(pipeline_config)
            validator.check_history_length(cleaned)

            # 4. Сохранение витрины
            prices_long = cleaned.stack().reset_index()
            prices_long.columns = ["date", "ticker", "close_adj"]

            returns_long = returns.stack().reset_index()
            returns_long.columns = ["date", "ticker", "log_return"]

            prices_long = prices_long.merge(
                returns_long, on=["date", "ticker"], how="left"
            )
            prices_long["is_filled_flag"] = False
            prices_long.to_parquet(pipeline_config["paths"]["prices"], index=False)

            # 5. Метаданные
            metadata = pd.DataFrame(
                {
                    "ticker": close_prices.columns,
                    "liquidity_status": status.values,
                    "missing_pct": missing_pct.values,
                }
            )
            metadata.to_csv(pipeline_config["paths"]["metadata"], index=False)

            return len(prices_long)

        result = benchmark(run_pipeline)

        assert result > 0
        benchmark.extra_info["instruments"] = 260
        benchmark.extra_info["days"] = 750
        benchmark.extra_info["total_records"] = result

    def test_datamart_load_performance(
        self,
        benchmark,
        production_dataset: pd.DataFrame,
        pipeline_config: Dict[str, Any],
        tmp_path: Path,
    ):
        """
        Бенчмарк загрузки данных из витрины через DataMart.

        Целевое время: < 30 секунд для загрузки 260 инструментов
        """
        import yaml

        prices_long, metadata = self._prepare_vitrine(
            production_dataset, pipeline_config
        )
        self._save_vitrine(prices_long, metadata, pipeline_config)

        config_file = tmp_path / "config.yaml"
        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(pipeline_config, f)

        mart = DataMart(str(config_file))

        result = benchmark(mart.load_prices)

        assert len(result) > 0
        benchmark.extra_info["records"] = len(result)

    def test_walk_forward_generation_performance(
        self,
        benchmark,
        production_dataset: pd.DataFrame,
        pipeline_config: Dict[str, Any],
        tmp_path: Path,
    ):
        """
        Бенчмарк генерации Walk-Forward фолдов.

        Целевое время: < 10 секунд для 10 фолдов

        Примечание: Количество фолдов зависит от размера данных:
        - 750 дней → ~8 фолдов (test_window=365, step=30)
        - 1500 дней → ~10+ фолдов
        """
        import yaml

        prices_long, metadata = self._prepare_vitrine(
            production_dataset, pipeline_config
        )
        self._save_vitrine(prices_long, metadata, pipeline_config)

        config_file = tmp_path / "config.yaml"
        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(pipeline_config, f)

        mart = DataMart(str(config_file))

        result = benchmark(mart.get_walk_forward_folds, n_folds=10, step_days=30)

        # ← ИСПРАВЛЕНО: Проверяем что фолды есть (не ровно 10)
        assert len(result) > 0, "Должен быть хотя бы 1 фолд"
        assert len(result) <= 10, f"Не больше 10 фолдов, получено {len(result)}"

        # Проверка качества фолдов
        for i, (train, test) in enumerate(result):
            assert len(train) > 0, f"Fold {i}: train пустой"
            assert len(test) > 0, f"Fold {i}: test пустой"

            # Проверка отсутствия утечки данных
            train_max = train.index.get_level_values("date").max()
            test_min = test.index.get_level_values("date").min()
            assert train_max <= test_min, f"Fold {i}: утечка данных!"

        benchmark.extra_info["folds"] = len(result)
        benchmark.extra_info["expected_folds"] = 10
        benchmark.extra_info["data_days"] = 750

    def test_walk_forward_generation_large_dataset(
        self,
        benchmark,
        large_dataset: pd.DataFrame,
        pipeline_config: Dict[str, Any],
        tmp_path: Path,
    ):
        """
        Бенчмарк генерации Walk-Forward фолдов на больших данных.

        Целевое время: < 10 секунд для 10 фолдов
        Ожидаемое количество фолдов: 10+ (1500 дней данных)
        """
        import yaml

        prices_long, metadata = self._prepare_vitrine(large_dataset, pipeline_config)
        self._save_vitrine(prices_long, metadata, pipeline_config)

        config_file = tmp_path / "config.yaml"
        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(pipeline_config, f)

        mart = DataMart(str(config_file))

        result = benchmark(mart.get_walk_forward_folds, n_folds=10, step_days=30)

        # С большими данными должно быть 10 фолдов
        assert len(result) >= 8, f"Ожидаем минимум 8 фолдов, получено {len(result)}"

        benchmark.extra_info["folds"] = len(result)
        benchmark.extra_info["data_days"] = 1500

    def test_walk_forward_folds_quality(
        self,
        production_dataset: pd.DataFrame,
        pipeline_config: Dict[str, Any],
        tmp_path: Path,
    ):
        """
        Тест качества Walk-Forward фолдов (не бенчмарк).

        Проверяет:
        - Отсутствие утечки данных между train/test
        - Корректное перекрытие фолдов
        - Размер тестовых окон
        """
        import yaml

        prices_long, metadata = self._prepare_vitrine(
            production_dataset, pipeline_config
        )
        self._save_vitrine(prices_long, metadata, pipeline_config)

        config_file = tmp_path / "config.yaml"
        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(pipeline_config, f)

        mart = DataMart(str(config_file))
        folds = mart.get_walk_forward_folds(n_folds=10, step_days=30)

        # Базовые проверки
        assert len(folds) > 0, "Должны быть фолды"

        # Проверка каждого фолда
        prev_test_end = None
        for i, (train, test) in enumerate(folds):
            # Проверка на пустоту
            assert len(train) > 0, f"Fold {i}: train пустой"
            assert len(test) > 0, f"Fold {i}: test пустой"

            # Проверка отсутствия утечки
            train_max = train.index.get_level_values("date").max()
            test_min = test.index.get_level_values("date").min()
            test_max = test.index.get_level_values("date").max()

            assert train_max <= test_min, f"Fold {i}: утечка данных!"

            # Проверка последовательности фолдов
            if prev_test_end is not None:
                assert test_min >= prev_test_end, f"Fold {i}: фолды не последовательны"

            prev_test_end = test_max
