# Методология расчёта параметров риска

- **Версия:** 0.2.0  
- **Дата:** 2026-03-12  
- **Статус:** В разработке
- **Связанные документы:** [index.md](index.md), [clustering.md](clustering.md), [regimes.md](regimes.md), [validation.md](validation.md), [PFE_мethodology_compliance.md](PFE_мethodology_compliance.md)

---

## 1. Обзор

Расчёт параметров риска — критический компонент Equity Model, обеспечивающий консервативную оценку Beta, волатильности и Haircuts для каждого актива с учётом:
- Длины истории (4 группы: A, B, C, D)
- Рыночного режима (4 активных из 9)
- Ликвидности инструмента
- Кризисного режима (Freeze)

**Выходные данные:**
| Параметр | Описание | Использование |
| :--- | :--- | :--- |
| `beta_adjusted` | Консервативная Beta | Monte Carlo симуляция |
| `sigma_adjusted` | Консервативная волатильность | VaR, PFE расчёт |
| `haircut_multiplier` | Множитель для Haircuts | Market Risk NCC |
| `liquidity_horizon` | Горизонт ликвидности | Liquidity Premium |

---

## 2. Базовые формулы

### 2.1. Волатильность

Для каждого актива $i$ в режиме $r$:

$$ \sigma_{adjusted, i, r} = \sigma_{base, i} \times M_{history, i} \times M_{regime, r} \times M_{liquidity, i} $$

**Где:**
| Параметр | Описание | Источник |
| :--- | :--- | :--- |
| $\sigma_{base, i}$ | Историческая волатильность (252 дня) | `returns_df.std() * √252` |
| $M_{history, i}$ | Множитель по группе истории | Таблица 2.1 |
| $M_{regime, r}$ | Множитель по режиму рынка | Таблица 2.2 |
| $M_{liquidity, i}$ | Премия за ликвидность | Таблица 2.3 |

### 2.2. Beta-коэффициент

$$ \beta_{adjusted, i} = \beta_{base, i} \times M_{history, i} $$

**Примечание:** Режим не влияет на Beta, только на волатильность.

### 2.3. Haircut

$$ \text{Haircut}_i = \text{Haircut}_{base} \times \text{HaircutMultiplier}_r \times M_{liquidity, i} $$

**Где:**
- $\text{Haircut}_{base}$ = 15% (базовый для акций)
- $\text{HaircutMultiplier}_r$ — по режиму (Таблица 2.2)

---

## 3. Множители

### 3.1. История (Conservative Approach)

Активы с короткой историей получают консервативные множители из-за меньшей статистической надёжности.

| Группа | Дней | Beta Mult | Sigma Mult | Обоснование |
| :--- | :--- | :--- | :--- | :--- |
| **A** | 0–30 | 1.30 | 1.20 | Минимум данных, высокая неопределённость |
| **B** | 30–100 | 1.20 | 1.10 | Недостаточно для EWMA |
| **C** | 100–200 | 1.05 | 1.05 | Переходная группа |
| **D** | 200+ | 1.00 | 1.00 | Эталонная группа (полная история) |

**Конфигурация:**
```yaml
conservative:
  group_A: {beta_multiplier: 1.30, sigma_multiplier: 1.20}
  group_B: {beta_multiplier: 1.20, sigma_multiplier: 1.10}
  group_C: {beta_multiplier: 1.05, sigma_multiplier: 1.05}
  group_D: {beta_multiplier: 1.00, sigma_multiplier: 1.00}
```

### 3.2. Режим рынка (4 активных Production режима)

| Параметр | BULL_LOW | BULL_HIGH | BEAR_LOW | BEAR_HIGH |
| :--- | :--- | :--- | :--- | :--- |
| **drift_multiplier** | 1.20 | 0.80 | 0.70 | 0.50 |
| **sigma_multiplier** | 0.80 | 1.30 | 1.00 | 1.50 |
| **correlation_adjustment** | -0.10 | +0.15 | +0.10 | +0.25 |
| **haircut_multiplier** | 0.90 | 1.20 | 1.10 | 1.50 |
| **liquidity_horizon_base** | 10 | 15 | 12 | 20 |

**Полная матрица 9 режимов (архитектура):**

| Режим | Drift Mult | Sigma Mult | Corr Adj | Haircut Mult | Liq Horizon |
| :--- | :--- | :--- | :--- | :--- | :--- |
| BULL_LOW | 1.20 | 0.80 | -0.10 | 0.90 | 10 |
| BULL_NORMAL | 1.00 | 1.00 | 0.00 | 1.00 | 10 |
| BULL_HIGH | 0.80 | 1.30 | +0.15 | 1.20 | 15 |
| NEUTRAL_LOW | 1.00 | 0.90 | 0.00 | 1.00 | 10 |
| NEUTRAL_NORMAL | 1.00 | 1.00 | 0.00 | 1.00 | 10 |
| NEUTRAL_HIGH | 0.90 | 1.20 | +0.10 | 1.10 | 12 |
| BEAR_LOW | 0.70 | 1.00 | +0.10 | 1.10 | 12 |
| BEAR_NORMAL | 0.60 | 1.20 | +0.15 | 1.25 | 15 |
| BEAR_HIGH | 0.50 | 1.50 | +0.25 | 1.50 | 20 |

**Конфигурация:**
```yaml
regimes:
  active: [BULL_LOW, BULL_HIGH, BEAR_LOW, BEAR_HIGH]
  parameters:
    BULL_LOW:
      drift_multiplier: 1.20
      sigma_multiplier: 0.80
      correlation_adjustment: -0.10
      haircut_multiplier: 0.90
      liquidity_horizon_base: 10
    # ... остальные режимы
```

### 3.3. Ликвидность (Liquidity Premium)

Коэффициент ликвидности рассчитывается как:

$$ \text{Liquidity Ratio} = \frac{\text{Торговых дней с данными}}{\text{Календарных дней в периоде}} $$

| Liquidity Ratio | Multiplier | Класс |
| :--- | :--- | :--- |
| ≥ 0.80 | 1.0 | Ликвидные |
| 0.60 – 0.80 | 1.2 | Средне-ликвидные |
| 0.40 – 0.60 | 1.5 | Низко-ликвидные |
| < 0.40 | 2.0 | Неликвидные |

**Конфигурация:**
```yaml
liquidity:
  threshold: 0.80
  liquidity_premium:
    0.80: 1.0
    0.60: 1.2
    0.40: 1.5
    0.0: 2.0
```

---

## 4. Детальный алгоритм расчёта

### 4.1. Шаг 1: Базовая оценка

```python
# Для каждого актива i
sigma_base[i] = std(returns[i, :reference_date]) * sqrt(252)
beta_base[i] = cov(returns[i], market_returns) / var(market_returns)
```

### 4.2. Шаг 2: Классификация по истории

```python
# Определение группы
if n_days < 30:
    group = 'A'
elif n_days < 100:
    group = 'B'
elif n_days < 200:
    group = 'C'
else:
    group = 'D'

M_history_beta = config['conservative'][f'group_{group}']['beta_multiplier']
M_history_sigma = config['conservative'][f'group_{group}']['sigma_multiplier']
```

### 4.3. Шаг 3: Определение режима

```python
# Multi-Indicator Score → Direction (Bull/Bear/Neutral)
# Volatility Overlay → Vol Level (Low/Normal/High)
# Комбинация → Режим (например, BEAR_HIGH)

regime = detect_regime(reference_date)
M_regime_sigma = config['regimes']['parameters'][regime]['sigma_multiplier']
M_regime_haircut = config['regimes']['parameters'][regime]['haircut_multiplier']
```

### 4.4. Шаг 4: Расчёт ликвидности

```python
liquidity_ratio = n_trading_days / n_calendar_days
M_liquidity = get_liquidity_multiplier(liquidity_ratio)
```

### 4.5. Шаг 5: Финальный расчёт

```python
beta_adjusted[i] = beta_base[i] * M_history_beta

sigma_adjusted[i] = (sigma_base[i] 
                     * M_history_sigma 
                     * M_regime_sigma 
                     * M_liquidity)

haircut[i] = 0.15 * M_regime_haircut * M_liquidity
```

---

## 5. Корректировка корреляций по режимам

### 5.1. Формула

$$ \rho_{adjusted, ij} = \text{clip}(\rho_{base, ij} + \Delta_{regime}, -1.0, 1.0) $$

### 5.2. Параметры по режимам

| Режим | Correlation Adjustment | Обоснование |
| :--- | :--- | :--- |
| BULL_LOW | -0.10 | Диверсификация работает |
| BULL_NORMAL | 0.00 | Базовые корреляции |
| BULL_HIGH | +0.15 | Напряжённость растёт |
| BEAR_LOW | +0.10 | Кризисные корреляции |
| BEAR_NORMAL | +0.15 | Умеренный стресс |
| BEAR_HIGH | +0.25 | "Все падают вместе" |

### 5.3. Ограничение Liquid-Illiquid

$$ \rho_{liquid-illiquid} = \min(\rho_{calculated}, 0.75) $$

**Обоснование:** Неликвидные активы имеют запаздывающие цены, что искусственно занижает корреляции.

---

## 6. GARCH параметры по уровням волатильности

Для моделирования волатильности в Monte Carlo используются режим-зависимые параметры GARCH(1,1):

| Уровень Vol | α (ARCH) | β (GARCH) | ω (Constant) |
| :--- | :--- | :--- | :--- |
| **Low** | 0.08 | 0.90 | 0.02 |
| **Normal** | 0.10 | 0.85 | 0.05 |
| **High** | 0.15 | 0.80 | 0.10 |

**Уравнение:**

$$ \sigma_t^2 = \omega + \alpha \cdot \epsilon_{t-1}^2 + \beta \cdot \sigma_{t-1}^2 $$

---

## 7. Кризисный режим (Freeze)

### 7.1. Триггеры активации

| Триггер | Порог | Источник |
| :--- | :--- | :--- |
| VIX-RUS | > 40 | `crisis.vix_threshold` |
| Просадка IMOEX | < -20% | `crisis.imoex_drawdown` |
| Средняя корреляция | > 0.90 | `crisis.correlation_spike` |

### 7.2. Действия при активации

1. Кластеризация замораживается на **63 дня**
2. Параметры риска обновляются **ежедневно** (по режиму)
3. Используются последние сохранённые кластеры
4. Все сигналы кризиса логируются

### 7.3. Параметры в кризисе

| Параметр | Значение |
| :--- | :--- |
| Sigma Multiplier | 1.50 (BEAR_HIGH) |
| Haircut Multiplier | 1.50 |
| Correlation Adjustment | +0.25 |
| Liquidity Horizon | 30 дней |

---

## 8. Интеграция с Monte Carlo симуляцией

### 8.1. Влияние на дрейф (μ)

| Режим | Дневной дрейф | Годовой дрейф |
| :--- | :--- | :--- |
| **Bull** | +0.03% до +0.08% | +8% до +20% |
| **Neutral** | -0.01% до +0.03% | -2% до +8% |
| **Bear** | -0.05% до -0.01% | -12% до -2% |

**Формула:**
$$ \mu_{adjusted} = \mu_{base} \times \text{drift\_multiplier}_r $$

### 8.2. Влияние на волатильность (σ)

$$ \sigma_{t} = \sigma_{adjusted} \times \sqrt{\text{GARCH}_t} $$

### 8.3. Влияние на корреляции

В симуляции для каждого дня $t$:
```python
if regime == 'BEAR_HIGH':
    corr_matrix = base_corr + 0.25
elif regime == 'BULL_LOW':
    corr_matrix = base_corr - 0.10
else:
    corr_matrix = base_corr
```

---

## 9. Соответствие PFE Methodology

### 9.1. Таблица соответствия

| Раздел Methodology | Требование | Реализация | Статус |
| :--- | :--- | :--- | :--- |
| **1.1 PFE(T, λ)** | Monte Carlo с режимами | 9 режимов, динамические параметры | Полное |
| **1.2 EAD** | EAD = α × max EPE, α = 1.4 | Применяется к максимальному exposure | Полное |
| **3.4.1 MR(T)*** | MR = Σ Sₗ × MRRₗ × \|Q\| | Haircuts зависят от Vol Overlay | Полное |
| **3.4.2 PR(T)*** | Процентный риск | High Vol → консервативные ставки | Полное |

### 9.2. Влияние на PFE

| Метрика | Без режимов | С режимами | Разница |
| :--- | :--- | :--- | :--- |
| **PFE (95%)** | 1.35 × начальная | 1.52 × начальная | **+13%** |
| **VaR (95%)** | -35% | -42% | **+20%** |
| **VaR (99%)** | -50% | -62% | **+24%** |
| **Макс. просадка** | -45% | -58% | **+29%** |

---

## 10. Практический пример расчёта

### 10.1. Входные данные

```
Актив: SBER
Группа истории: D (250 дней)
Ликвидность: 0.85 (Ликвидный)
Режим: BEAR_HIGH
σ_base: 25% годовых
β_base: 1.10
```

### 10.2. Расчёт

```python
# Множители
M_history_beta = 1.00   # Группа D
M_history_sigma = 1.00  # Группа D
M_regime_sigma = 1.50   # BEAR_HIGH
M_regime_haircut = 1.50 # BEAR_HIGH
M_liquidity = 1.0       # Liquidity ≥ 0.80

# Итоговые параметры
beta_adjusted = 1.10 * 1.00 = 1.10
sigma_adjusted = 25% * 1.00 * 1.50 * 1.0 = 37.5%
haircut = 15% * 1.50 * 1.0 = 22.5%
```

### 10.3. Выходные данные (cluster_mapping.csv)

| ticker | beta_base | beta_adjusted | sigma_base | sigma_adjusted | haircut_multiplier | regime |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| SBER | 1.10 | 1.10 | 0.25 | 0.375 | 1.50 | BEAR_HIGH |

---

## 11. Валидация и тестирование

### 11.1. Unit-тесты

| № | Тест | Ожидаемый результат |
| :--- | :--- | :--- |
| 3 | Liquidity multiplier | 0.90 -> 1.0, 0.50 -> 1.5, 0.30 -> 2.0 |
| 7 | Импутация пропусков | β в [0.5, 3.0] |
| 10 | Liquidity Premium | σ_adjusted > σ_base для неликвидных |
| 11 | Определение режима | Режим в списке активных |
| 12 | Проверка на кризис | Кризис обнаружен при триггерах |

### 11.2. Критерии качества

| Метрика | Целевое значение | Порог тревоги |
| :--- | :--- | :--- |
| σ_adjusted / σ_base | 1.0 – 3.0 | > 3.5 |
| β_adjusted / β_base | 1.0 – 1.5 | > 2.0 |
| Haircut | 10% – 40% | > 50% |
| Покрытие (все тикеры) | 100% | < 95% |

---

## 12. Конфигурация (YAML)

```yaml
# config/base.yaml

conservative:
  group_A: {beta_multiplier: 1.30, sigma_multiplier: 1.20}
  group_B: {beta_multiplier: 1.20, sigma_multiplier: 1.10}
  group_C: {beta_multiplier: 1.05, sigma_multiplier: 1.05}
  group_D: {beta_multiplier: 1.00, sigma_multiplier: 1.00}

liquidity:
  threshold: 0.80
  imputation_beta_clip: [0.5, 3.0]
  correlation_cap: 0.75
  liquidity_premium:
    0.80: 1.0
    0.60: 1.2
    0.40: 1.5
    0.0: 2.0

regimes:
  active: [BULL_LOW, BULL_HIGH, BEAR_LOW, BEAR_HIGH]
  parameters:
    BULL_LOW:
      drift_multiplier: 1.20
      sigma_multiplier: 0.80
      correlation_adjustment: -0.10
      haircut_multiplier: 0.90
      liquidity_horizon_base: 10
    BULL_HIGH:
      drift_multiplier: 0.80
      sigma_multiplier: 1.30
      correlation_adjustment: 0.15
      haircut_multiplier: 1.20
      liquidity_horizon_base: 15
    BEAR_LOW:
      drift_multiplier: 0.70
      sigma_multiplier: 1.00
      correlation_adjustment: 0.10
      haircut_multiplier: 1.10
      liquidity_horizon_base: 12
    BEAR_HIGH:
      drift_multiplier: 0.50
      sigma_multiplier: 1.50
      correlation_adjustment: 0.25
      haircut_multiplier: 1.50
      liquidity_horizon_base: 20

crisis:
  vix_threshold: 40
  imoex_drawdown: -0.20
  correlation_spike: 0.90
  freeze_duration_days: 63
```

---

## 13. Ограничения и допущения

| Ограничение | Влияние | Митигация |
| :--- | :--- | :--- |
| Нормальность доходностей | Недооценка хвостов | Jump-процесс в симуляции |
| Стационарность β внутри режима | Ошибки при сдвигах | Ежедневное обновление параметров |
| История < 30 дней | Низкая надёжность | Консервативные множители (1.30×) |
| Упрощённая ликвидность | Риск при замораживании | Liquidity premium + haircut |
| Лаг макро-данных | Устаревшие сигналы | Fallback на последнее значение |

---

## 14. Ссылки

| Документ | Описание |
| :--- | :--- |
| [index.md](index.md) | Общая методология модели |
| [clustering.md](clustering.md) | Детали кластеризации активов |
| [regimes.md](regimes.md) | Определение рыночных режимов |
| [DEVELOPMENT_PLAN.md](../DEVELOPMENT_PLAN.md) | План разработки проекта |
| [PFE_мethodology_compliance.md](PFE_мethodology_compliance.md) | Соответствие Методологии PFE расчётов |
| [2_Clustering_v2.ipynb](../../notebooks/2_Clustering_v2.ipynb) | Исходный ноутбук с реализацией |

---
