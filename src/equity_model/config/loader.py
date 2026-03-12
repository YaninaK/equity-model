# src/equity_model/config/loader.py
"""
Загрузчик конфигурации Equity Model.

Загружает, объединяет и валидирует YAML-конфигурацию.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

logger = logging.getLogger(__name__)

CONFIG_DIR = Path(__file__).parent.parent.parent / "config"

DEFAULT_FILES = [
    "base.yaml",
    "data.yaml",
    "clustering.yaml",
    "regimes.yaml",
    "risk.yaml",
    "simulation.yaml",
    "performance.yaml",
]


def load_config(config_files: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Загрузка и объединение конфигов.

    Parameters
    ----------
    config_files : list, optional
        Список файлов (по умолчанию все из DEFAULT_FILES)

    Returns
    -------
    dict
        Объединённая конфигурация

    Raises
    ------
    ValueError
        При критических ошибках валидации
    FileNotFoundError
        Если ни один файл не найден
    """
    files = config_files or DEFAULT_FILES
    config: Dict[str, Any] = {}
    loaded_count = 0

    for file_name in files:
        file_path = CONFIG_DIR / file_name
        if file_path.exists():
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                    if data:
                        config.update(data)
                        loaded_count += 1
            except Exception as e:
                logger.error(f"Ошибка чтения {file_name}: {e}")
                raise
        else:
            logger.warning(f"Файл не найден: {file_name}")

    if loaded_count == 0:
        raise FileNotFoundError("Ни один файл конфигурации не загружен")

    logger.info(f"Конфигурация загружена ({loaded_count} файлов)")

    # Валидация
    _validate_config(config)

    return config


def get_risk_config() -> Dict[str, Any]:
    """Конфигурация рисков (base + risk)."""
    return load_config(["base.yaml", "risk.yaml"])


def get_clustering_config() -> Dict[str, Any]:
    """Конфигурация кластеризации (base + clustering)."""
    return load_config(["base.yaml", "clustering.yaml"])


def get_regimes_config() -> Dict[str, Any]:
    """Конфигурация режимов (base + regimes)."""
    return load_config(["base.yaml", "regimes.yaml"])


def _validate_config(config: Dict[str, Any]) -> None:
    """
    Валидация критических параметров.

    Raises
    ------
    ValueError
        При критических ошибках
    """
    errors = []
    warnings = []

    # 1. Обязательные секции
    for section in ["clustering", "regimes", "crisis", "liquidity"]:
        if section not in config:
            errors.append(f"Отсутствует секция: {section}")

    # 2. Кризисные пороги
    if "crisis" in config:
        vix = config["crisis"].get("vix_threshold", 0)
        if vix < 20 or vix > 60:
            warnings.append(f"Подозрительный vix_threshold: {vix}")

        dd = config["crisis"].get("imoex_drawdown", 0)
        if dd > -0.10:
            warnings.append(f"Слишком мягкий imoex_drawdown: {dd}")

    # 3. Режимы
    if "regimes" in config:
        active = config["regimes"].get("active", [])
        if not active:
            errors.append("Нет активных режимов")

        params = config["regimes"].get("parameters", {})
        for regime in active:
            if regime not in params:
                errors.append(f"Режим {regime} не настроен в parameters")

    # 4. Ликвидность
    if "liquidity" in config:
        premium = config["liquidity"].get("liquidity_premium", {})
        if 0.80 not in premium:
            errors.append("Отсутствует порог ликвидности 0.80")

        beta_clip = config["liquidity"].get("imputation_beta_clip", [])
        if len(beta_clip) != 2 or beta_clip[0] >= beta_clip[1]:
            errors.append(f"Некорректный imputation_beta_clip: {beta_clip}")

    # Логирование
    for w in warnings:
        logger.warning(f"Validation: {w}")

    if errors:
        msg = "Ошибки конфигурации:\n" + "\n".join(errors)
        logger.error(msg)
        raise ValueError(msg)
