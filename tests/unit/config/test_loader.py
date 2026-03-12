# tests/unit/config/test_loader.py
"""
Модульные тесты для загрузчика конфигурации.
"""

import logging
from pathlib import Path
from unittest.mock import mock_open

import pytest
import yaml

from src.equity_model.config.loader import (
    DEFAULT_FILES,
    _validate_config,
    get_clustering_config,
    get_regimes_config,
    get_risk_config,
    load_config,
)

# ------------------------------------------------------------------------------
# Фикстуры
# ------------------------------------------------------------------------------


@pytest.fixture
def mock_filesystem(monkeypatch):
    """
    Фикстура для подмены Path.exists и встроенной open для конфигурационных файлов.
    Возвращает функцию, которая настраивает мок-данные для заданных файлов.
    """

    def _mock_filesystem(files_content: dict):
        """
        files_content: словарь имя_файла -> YAML строка или None (если файл отсутствует)
        """

        def mock_exists(path):
            # path – объект Path, нужно получить его имя
            return path.name in files_content and files_content[path.name] is not None

        def mock_open_func(path, *args, **kwargs):
            content = files_content.get(Path(path).name)
            if content is None:
                raise FileNotFoundError(f"Файл не найден: {path}")
            return mock_open(read_data=content).return_value

        monkeypatch.setattr(Path, "exists", mock_exists)
        monkeypatch.setattr("builtins.open", mock_open_func)

    return _mock_filesystem


@pytest.fixture
def base_config_yaml():
    """Базовая корректная YAML-конфигурация для тестов."""
    return """
clustering:
  method: kmeans
  n_clusters: 5

regimes:
  active: ["bull", "bear"]
  parameters:
    bull:
      volatility: 0.2
    bear:
      volatility: 0.4

crisis:
  vix_threshold: 30
  imoex_drawdown: -0.15

liquidity:
  liquidity_premium:
    0.80: 0.02
    0.50: 0.05
  imputation_beta_clip: [0.5, 1.5]
"""


# ------------------------------------------------------------------------------
# Тесты для load_config
# ------------------------------------------------------------------------------


def test_load_config_default(mock_filesystem, base_config_yaml):
    """Загрузка всех файлов по умолчанию с корректным YAML."""
    # Создаём мок-содержимое для всех файлов по умолчанию
    files_content = {fname: base_config_yaml for fname in DEFAULT_FILES}
    mock_filesystem(files_content)

    config = load_config()
    assert isinstance(config, dict)
    assert "clustering" in config
    assert config["clustering"]["method"] == "kmeans"
    # Проверяем, что слияние работает (последний файл перезаписывает) – везде одинаковое содержимое,
    # так что просто проверяем наличие ключа
    assert "regimes" in config


def test_load_config_custom_files(mock_filesystem, base_config_yaml):
    """Загрузка пользовательского списка файлов."""
    files_content = {"custom1.yaml": base_config_yaml, "custom2.yaml": base_config_yaml}
    mock_filesystem(files_content)

    config = load_config(["custom1.yaml", "custom2.yaml"])
    assert "clustering" in config


def test_load_config_missing_files(caplog, mock_filesystem, base_config_yaml):
    """Отсутствующие файлы вызывают предупреждения, но загрузка проходит, если есть хотя бы один."""
    files_content = {
        "base.yaml": base_config_yaml,
        "data.yaml": None,  # отсутствует
        "clustering.yaml": base_config_yaml,
    }
    mock_filesystem(files_content)

    with caplog.at_level(logging.WARNING):
        config = load_config(["base.yaml", "data.yaml", "clustering.yaml"])

    assert "Файл не найден: data.yaml" in caplog.text
    assert "clustering" in config
    assert "data" not in config  # потому что файл отсутствует


def test_load_config_no_files(mock_filesystem):
    """Если ни одного файла не существует, должно быть выброшено FileNotFoundError."""
    mock_filesystem({})  # файлов нет
    with pytest.raises(
        FileNotFoundError, match="Ни один файл конфигурации не загружен"
    ):
        load_config(["nonexistent.yaml"])


def test_load_config_read_error(mock_filesystem):
    """Ошибка чтения файла пробрасывается дальше."""
    files_content = {"bad.yaml": "некорректный yaml: ["}  # вызовет ошибку YAML
    mock_filesystem(files_content)

    with pytest.raises(yaml.YAMLError):
        load_config(["bad.yaml"])


# ------------------------------------------------------------------------------
# Тесты для вспомогательных функций-геттеров
# ------------------------------------------------------------------------------


def test_get_risk_config(monkeypatch):
    """get_risk_config вызывает load_config с правильными файлами."""
    called_with = None

    def mock_load_config(files):
        nonlocal called_with
        called_with = files
        return {"risk": "config"}

    monkeypatch.setattr("src.equity_model.config.loader.load_config", mock_load_config)
    result = get_risk_config()
    assert called_with == ["base.yaml", "risk.yaml"]
    assert result == {"risk": "config"}


def test_get_clustering_config(monkeypatch):
    """get_clustering_config вызывает load_config с правильными файлами."""
    called_with = None

    def mock_load_config(files):
        nonlocal called_with
        called_with = files
        return {"clustering": "config"}

    monkeypatch.setattr("src.equity_model.config.loader.load_config", mock_load_config)
    result = get_clustering_config()
    assert called_with == ["base.yaml", "clustering.yaml"]
    assert result == {"clustering": "config"}


def test_get_regimes_config(monkeypatch):
    """get_regimes_config вызывает load_config с правильными файлами."""
    called_with = None

    def mock_load_config(files):
        nonlocal called_with
        called_with = files
        return {"regimes": "config"}

    monkeypatch.setattr("src.equity_model.config.loader.load_config", mock_load_config)
    result = get_regimes_config()
    assert called_with == ["base.yaml", "regimes.yaml"]
    assert result == {"regimes": "config"}


# ------------------------------------------------------------------------------
# Тесты для _validate_config
# ------------------------------------------------------------------------------


def test_validate_config_valid(base_config_yaml):
    """Валидация корректной конфигурации (не должна вызывать исключений)."""
    config = yaml.safe_load(base_config_yaml)
    # Ошибок не ожидается
    _validate_config(config)


def test_validate_config_missing_sections():
    """Отсутствие обязательных секций вызывает ValueError."""
    config = {}
    with pytest.raises(ValueError) as excinfo:
        _validate_config(config)
    assert "Отсутствует секция: clustering" in str(excinfo.value)
    assert "regimes" in str(excinfo.value)
    assert "crisis" in str(excinfo.value)
    assert "liquidity" in str(excinfo.value)


def test_validate_config_crisis_warnings(caplog):
    """Кризисные пороги вне допустимого диапазона вызывают предупреждения."""
    config = {
        "clustering": {},
        "regimes": {"active": ["bull"], "parameters": {"bull": {}}},
        "crisis": {"vix_threshold": 10, "imoex_drawdown": -0.05},
        "liquidity": {
            "liquidity_premium": {0.80: 0.02},
            "imputation_beta_clip": [0.5, 1.5],
        },
    }
    with caplog.at_level(logging.WARNING):
        _validate_config(config)
    assert "Подозрительный vix_threshold: 10" in caplog.text
    assert "Слишком мягкий imoex_drawdown: -0.05" in caplog.text


def test_validate_config_regimes_errors():
    """Ошибки валидации режимов: отсутствие активных режимов или параметров."""
    config = {
        "clustering": {},
        "regimes": {"active": ["bull", "missing"], "parameters": {"bull": {}}},
        "crisis": {"vix_threshold": 30, "imoex_drawdown": -0.15},
        "liquidity": {
            "liquidity_premium": {0.80: 0.02},
            "imputation_beta_clip": [0.5, 1.5],
        },
    }
    with pytest.raises(ValueError) as excinfo:
        _validate_config(config)
    assert "Режим missing не настроен в parameters" in str(excinfo.value)


def test_validate_config_liquidity_errors():
    """Ошибки валидации ликвидности: отсутствие ключа 0.80 или некорректный imputation_beta_clip."""
    config = {
        "clustering": {},
        "regimes": {"active": ["bull"], "parameters": {"bull": {}}},
        "crisis": {"vix_threshold": 30, "imoex_drawdown": -0.15},
        "liquidity": {
            "liquidity_premium": {0.50: 0.02},  # отсутствует 0.80
            "imputation_beta_clip": [1.5, 0.5],  # неверный порядок
        },
    }
    with pytest.raises(ValueError) as excinfo:
        _validate_config(config)
    errors = str(excinfo.value)
    assert "Отсутствует порог ликвидности 0.80" in errors
    assert "Некорректный imputation_beta_clip: [1.5, 0.5]" in errors


def test_validate_config_empty_active_regimes():
    """Пустой список активных режимов вызывает ошибку."""
    config = {
        "clustering": {},
        "regimes": {"active": [], "parameters": {}},
        "crisis": {"vix_threshold": 30, "imoex_drawdown": -0.15},
        "liquidity": {
            "liquidity_premium": {0.80: 0.02},
            "imputation_beta_clip": [0.5, 1.5],
        },
    }
    with pytest.raises(ValueError) as excinfo:
        _validate_config(config)
    assert "Нет активных режимов" in str(excinfo.value)
