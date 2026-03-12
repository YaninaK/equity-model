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
git clone https://github.com/YaninaK/equity-model.git
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
├── README.md                    # Основная документация
├── CHANGELOG.md                 # История изменений
├── pyproject.toml               # Конфигурация проекта
├── uv.lock                      # Заблокированные зависимости
├── mkdocs.yml                   # Конфигурация документации
├── mypy.ini                     # Настройки mypy
│
├── src/equity_model/            # Исходный код пакета
│   ├── data/                    # Этап 1: Данные
│   ├── clustering/              # Этап 2: Кластеризация
│   ├── calibration/             # Этап 3: Калибровка
│   ├── short_term/              # Этап 4: Краткосрочная модель
│   ├── long_term/               # Этап 5: Долгосрочная модель
│   ├── stress/                  # Этап 6: Стресс-тесты
│   ├── comparison/              # Этап 7: Сравнение моделей
│   ├── backtest/                # Этап 8: Бэктестирование
│   ├── production/              # Этап 9: Оптимизация
│   └── reporting/               # Этап 10: Отчётность
│
├── tests/                       # Тесты
├── docs/                        # Документация
├── scripts/                     # Скрипты запуска
├── config/                      # Конфигурационные файлы
├── data/                        # Данные проекта
├── notebooks/                   # Jupyter ноутбуки
├── airflow/                     # Оркестрация пайплайнов
└── monitoring/                  # Мониторинг и алерты
```

---

## Документация

- **Дорожная карта**: `docs/ROADMAP.md`
- **План разработки**: `docs/DEVELOPMENT_PLAN.md`
- **Структура проекта**: `docs/STRUCTURE.md`
- **Паспорт методологии**: `docs/methodology/`
- **API документация**: `docs/api/` 
- **Отчёты**: `docs/reports/` 
- **Changelog**: `CHANGELOG.md`

### Локальный просмотр

```bash
# Запуск сервера документации
uv run mkdocs serve

# Открыть в браузере
# http://127.0.0.1:8000/
```
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