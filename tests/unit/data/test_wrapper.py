# tests/unit/data/test_wrapper.py

"""Тесты для модуля wrapper.py."""

from pathlib import Path

import pandas as pd
import pytest
import yaml

from equity_model.data.wrapper import DataMart, DataMartError


class TestDataMart:
    """Тесты для DataMart."""

    def test_init_success(self, temp_config_file):
        """Тест успешной инициализации."""
        mart = DataMart(temp_config_file)
        assert mart.prices_path is not None

    def test_load_prices_file_not_found(self, temp_config_file):
        """Тест загрузки несуществующего файла."""
        mart = DataMart(temp_config_file)
        with pytest.raises(DataMartError):
            mart.load_prices()

    def test_get_walk_forward_folds(
        self, temp_config_file, sample_prices, temp_data_dir
    ):
        """Тест генерации Walk-Forward фолдов."""
        # Загружаем конфигурацию и обновляем пути к временной директории
        with open(temp_config_file, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        # Обновляем пути к временной директории
        config["paths"]["prices"] = str(temp_data_dir / "prices_processed.parquet")
        config["paths"]["metadata"] = str(temp_data_dir / "metadata.csv")
        config["paths"]["processed_data"] = str(temp_data_dir)

        # Сохраняем обновлённую конфигурацию
        updated_config_file = temp_data_dir / "config.yaml"
        with open(updated_config_file, "w", encoding="utf-8") as f:
            yaml.dump(config, f)

        # Сохраняем тестовые данные в правильном формате (длинный формат с индексом)
        prices_long = sample_prices.stack().reset_index()
        prices_long.columns = ["date", "ticker", "close_adj"]
        prices_long["log_return"] = 0.0
        prices_long["is_filled_flag"] = False

        # Сохраняем в Parquet (путь из конфигурации)
        prices_long.to_parquet(config["paths"]["prices"], index=False)

        # Сохраняем метаданные
        metadata = pd.DataFrame(
            {
                "ticker": sample_prices.columns,
                "liquidity_status": ["Pass"] * len(sample_prices.columns),
                "missing_pct": [0.0] * len(sample_prices.columns),
            }
        )
        metadata.to_csv(config["paths"]["metadata"], index=False)

        # Создаём DataMart с обновлённой конфигурацией
        mart = DataMart(str(updated_config_file))

        # Тестируем генерацию фолдов
        folds = mart.get_walk_forward_folds(n_folds=3)

        assert len(folds) == 3
        for i, (train, test) in enumerate(folds):
            assert len(train) > 0, f"Fold {i}: train пустой"
            assert len(test) > 0, f"Fold {i}: test пустой"

            # Проверка отсутствия утечки
            train_max = train.index.get_level_values("date").max()
            test_min = test.index.get_level_values("date").min()
            assert train_max <= test_min, f"Fold {i}: утечка данных!"

    def test_load_prices_success(self, temp_config_file, temp_data_dir, sample_prices):
        """Тест успешной загрузки цен."""
        # Загружаем конфигурацию и обновляем пути
        with open(temp_config_file, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        config["paths"]["prices"] = str(temp_data_dir / "prices_processed.parquet")
        config["paths"]["metadata"] = str(temp_data_dir / "metadata.csv")

        updated_config_file = temp_data_dir / "config.yaml"
        with open(updated_config_file, "w", encoding="utf-8") as f:
            yaml.dump(config, f)

        # Сохраняем тестовые данные
        prices_long = sample_prices.stack().reset_index()
        prices_long.columns = ["date", "ticker", "close_adj"]
        prices_long["log_return"] = 0.0
        prices_long["is_filled_flag"] = False
        prices_long.to_parquet(config["paths"]["prices"], index=False)

        metadata = pd.DataFrame(
            {
                "ticker": sample_prices.columns,
                "liquidity_status": ["Pass"] * len(sample_prices.columns),
                "missing_pct": [0.0] * len(sample_prices.columns),
            }
        )
        metadata.to_csv(config["paths"]["metadata"], index=False)

        # Загружаем через DataMart
        mart = DataMart(str(updated_config_file))
        loaded = mart.load_prices()

        assert isinstance(loaded, pd.DataFrame)
        assert len(loaded) > 0
        assert "close_adj" in loaded.columns
        assert isinstance(loaded.index, pd.MultiIndex)
        assert "date" in loaded.index.names
        assert "ticker" in loaded.index.names

    def test_get_train_test_split(self, temp_config_file, temp_data_dir, sample_prices):
        """Тест разделения Train/Test."""
        # Загружаем конфигурацию и обновляем пути
        with open(temp_config_file, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        config["paths"]["prices"] = str(temp_data_dir / "prices_processed.parquet")
        config["paths"]["metadata"] = str(temp_data_dir / "metadata.csv")

        updated_config_file = temp_data_dir / "config.yaml"
        with open(updated_config_file, "w", encoding="utf-8") as f:
            yaml.dump(config, f)

        # Сохраняем тестовые данные
        prices_long = sample_prices.stack().reset_index()
        prices_long.columns = ["date", "ticker", "close_adj"]
        prices_long["log_return"] = 0.0
        prices_long["is_filled_flag"] = False
        prices_long.to_parquet(config["paths"]["prices"], index=False)

        metadata = pd.DataFrame(
            {
                "ticker": sample_prices.columns,
                "liquidity_status": ["Pass"] * len(sample_prices.columns),
                "missing_pct": [0.0] * len(sample_prices.columns),
            }
        )
        metadata.to_csv(config["paths"]["metadata"], index=False)

        # Тестируем разделение
        mart = DataMart(str(updated_config_file))
        train, test = mart.get_train_test_split(offset_days=365)

        assert len(train) > 0
        assert len(test) > 0

        # Проверка отсутствия утечки
        train_max = train.index.get_level_values("date").max()
        test_min = test.index.get_level_values("date").min()
        assert train_max < test_min
