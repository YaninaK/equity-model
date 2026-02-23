# Equity Model — Monte Carlo Simulation for Equity Pricing

## Описание проекта

**Equity Model** — разрабатываемая система прогнозирования цен акций на основе иерархической модели Монте-Карло. Поддерживает краткосрочное (до 90 дней) и долгосрочное (до 40 лет) моделирование с учётом рыночных режимов, стресс-сценариев и инфляции.

Проект находится на **начальной стадии разработки**. Данный репозиторий содержит план реализации, архитектуру и начальный код системы.

## Быстрый старт
### Требования
- **Python**: 3.11+
- **uv**: Установка uv (рекомендуется) или pip

### Установка

```bash
# Клонирование репозитория
git clone https://github.com/Yanina-Kutovaya/equity-model.git
cd equity-model

# Создание виртуального окружения и установка зависимостей
uv sync

# Альтернативно (без uv):
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# или .venv\Scripts\activate  # Windows
pip install -r requirements.txt
pip install -e .
```
---
## Структура проекта

```
equity-model/
├── README.md
├── .gitignore
├── .python-version
├── pyproject.toml
├── requirements.txt
├── config/                 # Конфигурационные файлы (в разработке)
├── data/                   # Данные (raw, processed, cache)
├── docs/                   # Документация и отчёты
├── notebooks/              # Jupyter ноутбуки для прототипирования
├── src/equity_model/       # Исходный код модели
│   ├── 1_data/               # Этап 1: Инфраструктура данных
│   ├── 2_clustering/         # Этап 2: Кластеризация 
│   ├── 3_calibration/        # Этап 3: Калибровка 
│   ├── 4_short_term/         # Этап 4: Краткосрочная модель
│   ├── 5_long_term/          # Этап 5: Долгосрочная модель
│   ├── 6_stress/             # Этап 6: Стресс-тестирование
│   ├── 7_comparison/         # Этап 7: Сравнение моделей
│   ├── 8_backtest/           # Этап 8: Бэктестирование
│   ├── 9_production/         # Этап 9: Оптимизация
│   └── 10_reporting/         # Этап 10: Отчётность
├── tests/                  # Тесты
├── scripts/                # Скрипты запуска
├── airflow/                # DAG для оркестрации
└── monitoring/             # Grafana дашборды
```
---

## Документация

- **Паспорт методологии**: `docs/methodology/`
- **API документация**: `docs/api/` 
- **Отчёты**: `docs/reports/` 
---

## Тестирование

### Запуск тестов (по мере разработки)

```bash
# Все тесты
pytest tests/ -v

# С покрытием кода
pytest tests/ -v --cov=src --cov-report=html
```

---