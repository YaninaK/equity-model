# Тестирование Equity Model

Этот документ описывает структуру тестов, правила написания и запуска тестов для проекта Equity Model.

---

## Структура тестов

```
tests/
├── __init__.py              # Инициализация пакета тестов
├── conftest.py              # Общие фикстуры pytest
├── mocks.py                 # Моки для внешних API (MOEX, банк)
├── README.md                # Этот файл
│
├── unit/                    # Модульные тесты (быстрые, изолированные)
│   ├── __init__.py
│   ├── data/                # Тесты модуля data
│   │   ├── __init__.py
│   │   ├── test_base.py
│   │   ├── test_moex_loader.py
│   │   ├── test_bank_loader.py
│   │   ├── test_factory.py
│   │   ├── test_loader.py 
│   │   ├── test_cleaner.py
│   │   ├── test_validator.py
│   │   └── test_wrapper.py
│   ├── clustering/          # Тесты модуля clustering (будущий Этап 2)
│   ├── calibration/         # Тесты модуля calibration (будущий Этап 3)
│   └── ...
│
├── integration/             # Интеграционные тесты (с внешними зависимостями)
│   ├── __init__.py
│   └── test_pipeline_integration.py
│
└── benchmarks/              # Тесты производительности
    ├── __init__.py
    ├── test_data_loader_bench.py
    ├── test_cleaner_bench.py
    └── test_pipeline_bench.py
```

---

## Быстрый старт

### Запуск всех тестов

```bash
# Все тесты (unit + integration + benchmarks)
uv run pytest tests/ -v

# Только unit-тесты (рекомендуется для повседневной разработки)
uv run pytest tests/unit/ -v

# С покрытием кода
uv run pytest tests/ -v --cov=src --cov-report=html

# Открыть отчёт о покрытии
start htmlcov/index.html  # Windows
open htmlcov/index.html   # Mac/Linux
```

### Запуск по типам тестов

| Тип тестов | Команда | Время | Зависимости |
| :--- | :--- | :--- | :--- |
| **Unit** | `pytest tests/unit/ -v` | ~10 сек | ❌ Нет |
| **Integration** | `pytest tests/integration/ -v -m integration` | ~2-5 мин | ✅ MOEX/Банк |
| **Benchmarks** | `pytest tests/benchmarks/ -v --benchmark-only` | ~1 мин | ❌ Нет |

---

## Конвенции написания тестов

### Именование файлов

```
test_<module>.py          # Например: test_moex_loader.py
```

### Именование классов тестов

```python
class Test<ClassName>:    # Например: TestMOEXDataSource
```

### Именование функций тестов

```python
def test_<method>_<condition>_<expected>():
    # Например:
    def test_load_prices_not_connected_raises_error():
    def test_connect_success_returns_true():
```

### Структура теста (AAA Pattern)

```python
def test_example():
    # Arrange (Подготовка)
    config = {'data': {'source': 'moex'}}
    loader = MOEXDataSource(config)
    
    # Act (Действие)
    with patch('equity_model.data.moex_loader.moexalgo', mock_moexalgo()):
        result = loader.connect()
    
    # Assert (Проверка)
    assert result is True
    assert loader.is_connected is True
```

---

## Использование моков

### Моки для внешних API

Все тесты в `tests/unit/` должны использовать моки из `tests/mocks.py`:

```python
from tests.mocks import mock_moexalgo, create_mock_prices

def test_load_prices_with_mock():
    with patch('equity_model.data.moex_loader.moexalgo', mock_moexalgo()):
        # Тест не требует реального подключения к MOEX
        ...
```

### Маркеры для тестов

```python
@pytest.mark.unit
def test_unit_example():
    """Unit тест без внешних зависимостей."""
    pass

@pytest.mark.integration
def test_integration_example():
    """Интеграционный тест с реальным API."""
    pass

@pytest.mark.benchmark
def test_performance_example():
    """Тест производительности."""
    pass
```

---

## Требования к покрытию

| Модуль | Минимальное покрытие | Критичность |
| :--- | :---: | :---: |
| `data/` | > 80% | Критично |
| `clustering/` | > 80% | Критично |
| `calibration/` | > 80% | Критично |
| `production/` | > 90% | Критично |
| `reporting/` | > 70% | Важно |

### Проверка покрытия

```bash
# Запуск с проверкой минимального покрытия
uv run pytest tests/ -v --cov=src --cov-fail-under=80

# Отчёт в терминале
uv run pytest tests/ -v --cov=src --cov-report=term-missing
```

---

## Фикстуры

### Общие фикстуры (`conftest.py`)

| Фикстура | Описание |
| :--- | :--- |
| `config` | Конфигурация проекта для тестов |
| `sample_prices` | Тестовые данные цен (504 дня) |
| `temp_config_file` | Временный файл конфигурации |
| `temp_data_dir` | Временная директория для данных |

### Пример использования фикстур

```python
def test_pipeline_with_fixtures(config, sample_prices, temp_data_dir):
    """Тест с использованием общих фикстур."""
    # config — готовая конфигурация
    # sample_prices — тестовые данные
    # temp_data_dir — временная папка (автоматически очищается)
    ...
```

---

## Маркеры pytest

### Доступные маркеры

| Маркер | Описание | Команда |
| :--- | :--- | :--- |
| `unit` | Unit тесты | `pytest -m unit` |
| `integration` | Интеграционные тесты | `pytest -m integration` |
| `benchmark` | Тесты производительности | `pytest -m benchmark` |
| `moex` | Тесты требующие MOEX | `pytest -m moex` |
| `bank` | Тесты требующие хранилище | `pytest -m bank` |
| `slow` | Медленные тесты (>1 сек) | `pytest -m "not slow"` |

### Настройка маркеров (`pyproject.toml`)

```toml
[tool.pytest.ini_options]
markers = [
    "unit: marks tests as unit tests",
    "integration: marks tests as integration tests",
    "benchmark: marks tests as performance benchmarks",
    "moex: marks tests that require MOEX connection",
    "bank: marks tests that require bank storage connection",
    "slow: marks tests as slow running"
]
```

---

## Тесты производительности

### Установка pytest-benchmark

```bash
uv add --dev pytest-benchmark
```

### Пример бенчмарка

```python
# tests/benchmarks/test_cleaner_bench.py

import pytest
import pandas as pd
import numpy as np

from equity_model.data.cleaner import DataCleaner


@pytest.fixture
def large_prices():
    """Большие данные для тестов производительности."""
    dates = pd.date_range('2020-01-01', periods=5000, freq='B')
    tickers = [f'TICKER{i}' for i in range(100)]
    
    data = {}
    for ticker in tickers:
        data[ticker] = np.random.randn(5000).cumsum() + 100
    
    return pd.DataFrame(data, index=dates)


def test_forward_fill_performance(benchmark, large_prices):
    """Бенчмарк производительности forward fill."""
    cleaner = DataCleaner({'data': {'max_forward_fill_days': 5}})
    
    result = benchmark(cleaner.forward_fill, large_prices)
    
    assert result.shape == large_prices.shape
```

### Запуск бенчмарков

```bash
# Только бенчмарки
uv run pytest tests/benchmarks/ -v --benchmark-only

# Сравнение с предыдущими результатами
uv run pytest tests/benchmarks/ -v --benchmark-compare

# Экспорт результатов в JSON
uv run pytest tests/benchmarks/ -v --benchmark-json=benchmark_results.json
```

---

## CI/CD Интеграция

### GitHub Actions (`.github/workflows/tests.yml`)

```yaml
name: Tests

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install uv
        uses: astral-sh/setup-uv@v3
      
      - name: Install dependencies
        run: uv sync --dev
      
      - name: Run unit tests
        run: uv run pytest tests/unit/ -v --cov=src --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v4
        with:
          files: ./coverage.xml
```

---

## Частые ошибки

| Ошибка | Причина | Решение |
| :--- | :--- | :--- |
| `ModuleNotFoundError` | Пакет не установлен | `uv sync --dev` |
| `Fixture not found` | Фикстура не в conftest.py | Переместить в `tests/conftest.py` |
| `Mock not working` | Неправильный путь патча | Использовать полный путь: `package.module.Class` |
| `Tests too slow` | Нет моков для внешних API | Добавить моки из `tests/mocks.py` |
| `Coverage too low` | Недостаточно тестов | Добавить тесты для непокрытых функций |

---

## Чек-лист перед коммитом

```bash
# 1. Запустить все unit-тесты
uv run pytest tests/unit/ -v

# 2. Проверить покрытие кода
uv run pytest tests/unit/ -v --cov=src --cov-fail-under=80

# 3. Проверить типизацию
uv run mypy src/

# 4. Проверить форматирование
uv run black src/ tests/ --check
uv run isort src/ tests/ --check

# 5. Убедиться, что интеграционные тесты помечены маркером
#    (чтобы не запускались в CI по умолчанию)
```

---

*Последнее обновление: 2026-02-24*  
*Версия документа: 1.0*