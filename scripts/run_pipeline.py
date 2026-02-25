#!/usr/bin/env python3
"""Запуск полного пайплайна обработки данных."""

import logging
import sys
from pathlib import Path
from typing import Any, Dict

import pandas as pd
import yaml

# Добавляем src в path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from equity_model.data.cleaner import DataCleaner
from equity_model.data.loader import DataLoader, DataLoaderError
from equity_model.data.validator import DataValidator
from equity_model.data.wrapper import DataMart, DataMartError


def setup_logging(config: Dict[str, Any]) -> None:
    """
    Настройка логирования.

    Args:
        config: Конфигурация из YAML.
    """
    log_config = config.get("logging", {})
    log_level = getattr(logging, log_config.get("level", "INFO"))
    log_format = log_config.get(
        "format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    log_file = log_config.get("file", "logs/pipeline.log")

    # Создаём директорию для логов
    Path(log_file).parent.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )


def load_config(config_path: str = "config/base.yaml") -> Dict[str, Any]:
    """
    Загрузка конфигурации.

    Args:
        config_path: Путь к файлу конфигурации.

    Returns:
        Словарь с конфигурацией.
    """
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def main() -> int:
    """
    Главная функция пайплайна.

    Returns:
        Код завершения (0 = успех, 1 = ошибка).
    """
    try:
        logger = logging.getLogger(__name__)
        logger.info("🚀 Запуск пайплайна обработки данных...")

        # 1. Загрузка конфигурации
        config = load_config()
        setup_logging(config)

        # 2. Инициализация компонентов
        loader = DataLoader()
        cleaner = DataCleaner(config)
        validator = DataValidator(config)

        # 3. Загрузка сырых данных (пример для тикеров)
        tickers = ["SBER.ME", "GAZP.ME", "LKOH.ME", "YNDX.ME", "TCSG.ME"]
        logger.info(f"Загрузка данных для {len(tickers)} тикеров")
        raw_data = loader.load_from_yahoo(tickers, period="3y")
        loader.save_raw(raw_data, "raw_prices.parquet")

        # 4. Очистка и обработка
        close_prices = raw_data["Close"]
        logger.info(f"Цены закрытия: {close_prices.shape}")

        # Фильтрация по ликвидности
        missing_pct = close_prices.apply(lambda x: cleaner.calculate_missing_pct(x))
        filtered_prices, liquidity_status = cleaner.filter_by_liquidity(
            close_prices, missing_pct
        )
        logger.info(
            f"После фильтрации ликвидности: {filtered_prices.shape[1]} инструментов"
        )

        # Заполнение пропусков
        cleaned_prices = cleaner.forward_fill(filtered_prices)

        # Расчёт доходностей
        log_returns = cleaner.calculate_log_returns(cleaned_prices)

        # Флаги заполнений
        fill_flags = cleaner.create_fill_flag(filtered_prices, cleaned_prices)

        # 5. Валидация
        history_check = validator.check_history_length(cleaned_prices)
        n_passed = sum(history_check.values())
        logger.info(
            f"✅ Проверка истории: {n_passed}/{len(history_check)} инструментов"
        )

        # 6. Сохранение витрины (ДЛИННЫЙ ФОРМАТ)
        logger.info("Сохранение витрины данных в длинном формате...")
        prices_long = cleaned_prices.stack().reset_index()
        prices_long.columns = ["date", "ticker", "close_adj"]

        # Добавляем логарифмические доходности
        returns_long = log_returns.stack().reset_index()
        returns_long.columns = ["date", "ticker", "log_return"]
        prices_long = prices_long.merge(returns_long, on=["date", "ticker"], how="left")

        # Добавляем флаги заполнений
        flags_long = fill_flags.stack().reset_index()
        flags_long.columns = ["date", "ticker", "is_filled_flag"]
        prices_long = prices_long.merge(flags_long, on=["date", "ticker"], how="left")

        # Сохраняем в Parquet
        prices_long.to_parquet(config["paths"]["prices"], index=False)
        logger.info(f"💾 Данные сохранены в {config['paths']['prices']}")

        # 7. Сохранение метаданных
        metadata = pd.DataFrame(
            {
                "ticker": close_prices.columns,
                "liquidity_status": liquidity_status.values,
                "missing_pct": missing_pct.values,
            }
        )
        metadata.to_csv(config["paths"]["metadata"], index=False)
        logger.info(f"📋 Метаданные сохранены в {config['paths']['metadata']}")

        # 8. Проверка DataMart
        logger.info("Проверка DataMart...")
        mart = DataMart()
        loaded_prices = mart.load_prices()
        logger.info(f"✅ DataMart загрузил {len(loaded_prices)} записей")

        # 9. Проверка Walk-Forward фолдов
        folds = mart.get_walk_forward_folds(n_folds=3)
        logger.info(f"✅ Сгенерировано {len(folds)} фолдов для Walk-Forward")

        logger.info("✅ Пайплайн завершён успешно!")
        return 0

    except (DataLoaderError, DataMartError) as e:
        logging.error(f"❌ Ошибка пайплайна: {e}")
        return 1
    except Exception as e:
        logging.exception(f"❌ Неожиданная ошибка: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
