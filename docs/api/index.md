
# API Reference

> **Статус:** Модуль `data` реализован. Требуется настройка доступа к источникам данных.

---

## Примечание

Для работы с реальными данными требуется настройка доступа:

| Источник | Статус | Требования |
| :--- | :---: | :--- |
| **MOEX** | Требуется настройка | Проверить доступность данных без подписки |
| **Хранилище банка** | Внутренний доступ | Требуется доступ к внутренней инфраструктуре |
| **Локальные данные** | Готово | Работа с Parquet/CSV файлами |

> Для разработки используются моки и локальные данные. Интеграционные тесты помечены `@pytest.mark.skip` по умолчанию.

---

## Реализованные модули

### equity_model.__version__

Информация о версии пакета.

::: equity_model.__version__
    options:
      show_root_heading: true
      show_if_no_docstring: false
      show_signature: true
      show_source: false

---

### equity_model.data

Модуль загрузки, очистки и управления данными для 260+ инструментов.

#### Ограничения источников данных

| Класс | Статус | Примечание |
| :--- | :--- | :--- |
| `MOEXDataSource` | Требуется настройка | Проблемы доступности данных |
| `BankStorageDataSource` | Внутренний | Требуется доступ к хранилищу банка |
| `DataLoader` | Готов | Работает с локальными файлами |

---

#### Источники данных (абстракции)

::: equity_model.data.base.BaseDataSource
    options:
      show_root_heading: true
      show_if_no_docstring: false
      show_signature: true
      show_source: false
      members:
        - connect
        - disconnect
        - load_prices
        - load_dividends
        - load_metadata
        - is_connected

::: equity_model.data.moex_loader.MOEXDataSource
    options:
      show_root_heading: true
      show_if_no_docstring: false
      show_signature: true
      show_source: false

::: equity_model.data.bank_loader.BankStorageDataSource
    options:
      show_root_heading: true
      show_if_no_docstring: false
      show_signature: true
      show_source: false

---

#### Фабрика и загрузчик

::: equity_model.data.factory.DataSourceFactory
    options:
      show_root_heading: true
      show_if_no_docstring: false
      show_signature: true
      show_source: false
      members:
        - register
        - create
        - get_available_sources

::: equity_model.data.loader.DataLoader
    options:
      show_root_heading: true
      show_if_no_docstring: false
      show_signature: true
      show_source: false
      members:
        - load_prices
        - load_dividends
        - load_metadata
        - save_raw
        - load_raw

---

#### Обработка данных

::: equity_model.data.cleaner.DataCleaner
    options:
      show_root_heading: true
      show_if_no_docstring: false
      show_signature: true
      show_source: false
      members:
        - calculate_missing_pct
        - filter_by_liquidity
        - forward_fill
        - adjust_dividends
        - calculate_log_returns
        - create_fill_flag

::: equity_model.data.validator.DataValidator
    options:
      show_root_heading: true
      show_if_no_docstring: false
      show_signature: true
      show_source: false
      members:
        - check_history_length
        - check_no_negative_prices
        - check_no_future_leak
        - validate_split

---

#### Доступ к витрине данных

::: equity_model.data.wrapper.DataMart
    options:
      show_root_heading: true
      show_if_no_docstring: false
      show_signature: true
      show_source: false
      members:
        - load_prices
        - load_metadata
        - get_train_test_split
        - get_walk_forward_folds

---

#### Обработка исключений

::: equity_model.data.base.DataSourceError
    options:
      show_root_heading: true
      show_if_no_docstring: false
      show_signature: true
      show_source: false

::: equity_model.data.loader.DataLoaderError
    options:
      show_root_heading: true
      show_if_no_docstring: false
      show_signature: true
      show_source: false

::: equity_model.data.wrapper.DataMartError
    options:
      show_root_heading: false
      show_if_no_docstring: false
      show_signature: true
      show_source: false

---

## Модули в разработке

| Модуль | Этап | Статус | Описание |
| :--- | :---: | :---: | :--- |
| `equity_model.data` | 1 | В разработке | Загрузка, очистка, валидация данных |
| `equity_model.clustering` | 2 | Запланировано | Кластеризация активов по корреляциям |
| `equity_model.calibration` | 3 | Запланировано | Калибровка параметров модели |
| `equity_model.short_term` | 4 | Запланировано | Краткосрочная модель (< 90 дней) |
| `equity_model.long_term` | 5 | Запланировано | Долгосрочная модель (до 40 лет) |
| `equity_model.stress` | 6 | Запланировано | Стресс-тестирование и сценарии |
| `equity_model.comparison` | 7 | Запланировано | Сравнение моделей |
| `equity_model.backtest` | 8 | Запланировано | Бэктестирование стратегии |
| `equity_model.production` | 9 | Запланировано | Production пайплайн |
| `equity_model.reporting` | 10 | Запланировано | Отчётность и визуализация |

---

## Примеры использования

### Работа с локальными данными (рекомендуется)

```python
from equity_model.data.loader import DataLoader
import pandas as pd
import numpy as np

# Инициализация загрузчика
loader = DataLoader("config/base.yaml")

# Загрузка из локального Parquet файла
prices = loader.load_raw("data/raw/historical_prices.parquet")

# Или создание тестовых данных
tickers = ['SBER', 'GAZP', 'LKOH']
dates = pd.date_range('2023-01-01', periods=500, freq='B')
prices = pd.DataFrame(
    {t: np.random.randn(500).cumsum() + 100 for t in tickers},
    index=dates
)
```

### Загрузка из MOEX (требуется настройка)

```python
from equity_model.data.loader import DataLoader

loader = DataLoader("config/base.yaml")

# Загрузка цен (требует подключения к API)
prices = loader.load_prices(
    tickers=['SBER', 'GAZP', 'LKOH'],
    start_date='2023-01-01',
    end_date='2023-12-31'
)
```

### Загрузка из хранилища банка (внутренний доступ)

```python
# Требуется доступ к внутренней инфраструктуре банка
# Настройка в config/base.yaml:
# data:
#   source: bank_storage
#   bank_storage:
#     host: internal-db.vtb.ru
#     ...

loader = DataLoader("config/base.yaml")
prices = loader.load_prices(tickers=['SBER', 'GAZP'])
```

### Очистка и обработка данных

```python
from equity_model.data.cleaner import DataCleaner

config = {
    'data': {
        'liquidity_threshold': 0.20,
        'max_forward_fill_days': 5
    }
}

cleaner = DataCleaner(config)

# Заполнение пропусков
cleaned = cleaner.forward_fill(prices)

# Расчёт доходностей
returns = cleaner.calculate_log_returns(cleaned)
```

### Walk-Forward валидация

```python
from equity_model.data.wrapper import DataMart

mart = DataMart("config/base.yaml")

# Загрузка данных из витрины
prices = mart.load_prices()

# Генерация фолдов
folds = mart.get_walk_forward_folds(n_folds=10, step_days=30)

for i, (train, test) in enumerate(folds):
    print(f"Fold {i}: {len(train)} train, {len(test)} test")
```

---

## Настройка источников данных

### Конфигурация MOEX

```yaml
# config/base.yaml
data:
  source: moex
  
  moex:
    exchange: MOEX
    market: stock
    board: TQBR  # Основной режим торгов
```

---

### Конфигурация хранилища банка

```yaml
# config/base.yaml
data:
  source: bank_storage
  
  bank_storage:
    host: internal-db.vtb.ru
    port: 5432
    database: market_data
    schema: equity
    table: daily_prices
    auth_method: kerberos
```

**Требуется:**
- Доступ к внутренней сети банка
- Настройка Kerberos аутентификации
- Доступ к таблице `equity.daily_prices`

---

### Конфигурация локальных данных

```yaml
# config/base.yaml
data:
  source: local  # или использовать DataLoader напрямую
  
paths:
  raw_data: data/raw
  processed_data: data/processed
```

**Работает без внешних зависимостей**

---

## Тестирование

### Запуск тестов модуля data

```bash
# Все unit-тесты (не требуют доступа к API)
uv run pytest tests/unit/data/ -v

# Все бенчмарки (используют синтетические данные)
uv run pytest tests/benchmarks/ -v --benchmark-only

# Интеграционные тесты (пропущены по умолчанию)
uv run pytest tests/integration/ -v

# Запустить интеграционные тесты (требуется доступ к API)
uv run pytest tests/integration/ -v --run-skipped

# Покрытие кода
uv run pytest tests/unit/data/ -v --cov=src/equity_model/data --cov-report=term
```

---

## См. также

| Документ | Ссылка |
| :--- | :--- |
| Методология | [methodology/index.md](../methodology/index.md) |
| Дорожная карта | [../ROADMAP.md](../ROADMAP.md) |
| План разработки | [../DEVELOPMENT_PLAN.md](../DEVELOPMENT_PLAN.md) |
| Структура проекта | [../STRUCTURE.md](../STRUCTURE.md) |
| Автоматически генерируемые отчёты | [../reports/index.md](../reports/index.md) |
| Настройка доступа к данным | [../DATA_ACCESS.md](../DATA_ACCESS.md) |

---

- **Последнее обновление:** 2026-02-25
- **Версия документации:** 1.0 (Этап 1 в разаработке)
- **Статус доступа:** доступ только к локальным данным

---
