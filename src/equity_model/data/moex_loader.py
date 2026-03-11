# src/equity_model/data/moex_loader.py

"""Загрузчик данных с Московской Биржи через moexalgo."""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import pandas as pd

from .base import BaseDataSource, DataSourceError

logger = logging.getLogger(__name__)


class MOEXDataSource(BaseDataSource):
    """Источник данных для Московской Биржи."""

    def __init__(self, config: Dict[str, Any]) -> None:
        """Инициализация MOEX источника данных."""
        super().__init__(config)
        self.moex_config = config.get("data", {}).get("moex", {})
        self._client = None

    def connect(self) -> bool:
        """
        Инициализация клиента moexalgo.

        Returns:
            True если подключение успешно.

        Raises:
            DataSourceError: Если moexalgo не установлен.
        """
        try:
            # ← ЛЕНИВЫЙ ИМПОРТ (внутри метода)
            import moexalgo

            self._client = moexalgo
            self._connected = True
            logger.info("MOEX источник данных подключён")
            return True
        except ImportError as e:
            logger.error("moexalgo не установлен. Установите: pip install moexalgo")
            raise DataSourceError(f"moexalgo not installed: {e}") from e
        except SyntaxError as e:
            logger.error(f"moexalgo несовместим с Python: {e}")
            raise DataSourceError(
                f"moexalgo syntax error (Python version mismatch): {e}"
            ) from e
        except Exception as e:
            logger.error(f"Ошибка подключения к MOEX: {e}")
            raise DataSourceError(f"Failed to connect to MOEX: {e}") from e

    def disconnect(self) -> None:
        """Закрытие соединения."""
        self._connected = False
        logger.info("MOEX источник данных отключён")

    def load_prices(
        self,
        tickers: List[str],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Загрузка исторических цен с MOEX.

        Args:
            tickers: Список тикеров (например, ['SBER', 'GAZP']).
            start_date: Начальная дата в формате YYYY-MM-DD.
            end_date: Конечная дата в формате YYYY-MM-DD.

        Returns:
            DataFrame с колонками: date, ticker, open, high, low, close, volume.
            Пустой DataFrame если tickers пуст.

        Raises:
            DataSourceError: Если загрузка не удалась.
        """
        if not self._connected:
            raise DataSourceError("Сначала вызовите connect()")

        # ← ДОБАВЛЕНО: Обработка пустого списка тикеров
        if not tickers:
            logger.warning("Пустой список тикеров, возвращаем пустой DataFrame")
            return pd.DataFrame(
                columns=["date", "ticker", "open", "high", "low", "close", "volume"]
            )

        try:
            logger.info(f"Загрузка цен MOEX для {len(tickers)} тикеров")

            # Устанавливаем даты по умолчанию
            if end_date is None:
                end_date = datetime.now().strftime("%Y-%m-%d")
            if start_date is None:
                start_date = (datetime.now() - timedelta(days=3 * 365)).strftime(
                    "%Y-%m-%d"
                )

            all_data = []

            for ticker in tickers:
                try:
                    # Загрузка данных через moexalgo
                    board = self.moex_config.get("board", "TQBR")
                    data = self._client.trades(
                        code=ticker, board=board, from_date=start_date, to_date=end_date
                    )

                    if data is not None and len(data) > 0:
                        data["ticker"] = ticker
                        all_data.append(data)
                        logger.debug(f"Загружено {len(data)} записей для {ticker}")
                    else:
                        logger.warning(f"Нет данных для {ticker}")

                except Exception as e:
                    logger.warning(f"Ошибка загрузки {ticker}: {e}")
                    continue

            if not all_data:
                raise DataSourceError(
                    "Не удалось загрузить данные ни для одного тикера"
                )

            result = pd.concat(all_data, ignore_index=True)

            # Приведение к стандартному формату
            result = self._normalize_columns(result)

            logger.info(f"Загружено {len(result)} записей всего")
            return result

        except Exception as e:
            logger.error(f"Ошибка загрузки цен MOEX: {e}")
            raise DataSourceError(f"Failed to load MOEX prices: {e}") from e

    def load_dividends(
        self,
        tickers: List[str],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Optional[pd.DataFrame]:
        """Загрузка данных по дивидендам с MOEX."""
        if not self._connected:
            raise DataSourceError("Сначала вызовите connect()")

        try:
            logger.info(f"Загрузка дивидендов MOEX для {len(tickers)} тикеров")

            all_data = []

            for ticker in tickers:
                try:
                    data = self._client.dividends(code=ticker)

                    if data is not None and len(data) > 0:
                        data["ticker"] = ticker
                        all_data.append(data)

                except Exception as e:
                    logger.debug(f"Нет дивидендов для {ticker}: {e}")
                    continue

            if not all_data:
                logger.warning("Дивиденды не доступны")
                return None

            result = pd.concat(all_data, ignore_index=True)
            logger.info(f"Загружено {len(result)} записей дивидендов")
            return result

        except Exception as e:
            logger.warning(f"Ошибка загрузки дивидендов: {e}")
            return None

    def load_metadata(self, tickers: List[str]) -> pd.DataFrame:
        """Загрузка метаданных по инструментам с MOEX."""
        if not self._connected:
            raise DataSourceError("Сначала вызовите connect()")

        try:
            logger.info(f"Загрузка метаданных MOEX для {len(tickers)} тикеров")

            all_data = []

            for ticker in tickers:
                try:
                    info = self._client.get_info(code=ticker)

                    if info:
                        all_data.append(
                            {
                                "ticker": ticker,
                                "name": info.get("name", ""),
                                "sector": info.get("sector", "Unknown"),
                                "listing_date": info.get("listing_date", None),
                                "currency": info.get("currency", "RUB"),
                                "market": info.get("market", "stock"),
                            }
                        )

                except Exception as e:
                    logger.debug(f"Нет метаданных для {ticker}: {e}")
                    continue

            if not all_data:
                logger.warning(
                    "Метаданные не доступны, используем значения по умолчанию"
                )
                return pd.DataFrame(
                    {
                        "ticker": tickers,
                        "sector": "Unknown",
                        "listing_date": None,
                        "currency": "RUB",
                    }
                )

            result = pd.DataFrame(all_data)
            logger.info(f"Загружены метаданные для {len(result)} тикеров")
            return result

        except Exception as e:
            logger.warning(f"Ошибка загрузки метаданных: {e}")
            return pd.DataFrame({"ticker": tickers})

    def _normalize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Приведение колонок к стандартному формату."""
        column_mapping = {
            "date": "date",
            "DATETIME": "date",
            "OPEN": "open",
            "HIGH": "high",
            "LOW": "low",
            "CLOSE": "close",
            "VOLUME": "volume",
            "VALUE": "value",
        }

        df = df.rename(
            columns={k: v for k, v in column_mapping.items() if k in df.columns}
        )

        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"])

        return df
