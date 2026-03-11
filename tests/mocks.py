# tests/mocks.py

"""Моки для внешних зависимостей (MOEX, хранилище банка)."""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock

import pandas as pd


class MockMOEXClient:
    """Мок клиента MOEX для тестов."""

    @staticmethod
    def trades(
        code: str, board: str = "TQBR", from_date: str = None, to_date: str = None
    ) -> pd.DataFrame:
        """Мок загрузки торговых данных."""
        if to_date is None:
            to_date = datetime.now()
        else:
            to_date = pd.to_datetime(to_date)

        if from_date is None:
            from_date = to_date - timedelta(days=365)
        else:
            from_date = pd.to_datetime(from_date)

        dates = pd.date_range(from_date, to_date, freq="B")

        return pd.DataFrame(
            {
                "date": dates,
                "OPEN": [100.0 + i * 0.1 for i in range(len(dates))],
                "HIGH": [102.0 + i * 0.1 for i in range(len(dates))],
                "LOW": [99.0 + i * 0.1 for i in range(len(dates))],
                "CLOSE": [101.0 + i * 0.1 for i in range(len(dates))],
                "VOLUME": [1000000] * len(dates),
            }
        )

    @staticmethod
    def dividends(code: str) -> pd.DataFrame:
        """Мок загрузки дивидендов."""
        return pd.DataFrame(
            {"date": [datetime(2023, 6, 1)], "amount": [10.0], "ticker": [code]}
        )

    @staticmethod
    def get_info(code: str) -> Dict[str, Any]:
        """Мок получения информации об инструменте."""
        return {
            "name": f"{code} Company",
            "sector": "Technology",
            "listing_date": "2010-01-01",
            "currency": "RUB",
            "market": "stock",
        }


class MockBankStorage:
    """Мок хранилища банка для тестов."""

    def __init__(self) -> None:
        self._connected = False

    def connect(self) -> bool:
        """Мок подключения."""
        self._connected = True
        return True

    def disconnect(self) -> None:
        """Мок отключения."""
        self._connected = False

    def execute_query(self, query: str, params: tuple = None) -> pd.DataFrame:
        """Мок выполнения SQL запроса."""
        return pd.DataFrame(
            {"date": [datetime.now()], "ticker": ["TEST"], "close": [100.0]}
        )


def mock_moexalgo() -> MagicMock:
    """Создание мока для библиотеки moexalgo."""
    mock = MagicMock()
    mock.trades = MockMOEXClient.trades
    mock.dividends = MockMOEXClient.dividends
    mock.get_info = MockMOEXClient.get_info
    return mock


def create_mock_prices(tickers: List[str], days: int = 504) -> pd.DataFrame:
    """Создание тестовых данных цен."""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    dates = pd.date_range(start_date, end_date, freq="B")

    all_data = []
    for ticker in tickers:
        for i, date in enumerate(dates):
            all_data.append(
                {
                    "date": date,
                    "ticker": ticker,
                    "open": 100.0 + i * 0.1,
                    "high": 102.0 + i * 0.1,
                    "low": 99.0 + i * 0.1,
                    "close": 101.0 + i * 0.1,
                    "volume": 1000000,
                }
            )

    return pd.DataFrame(all_data)


def create_mock_metadata(tickers: List[str]) -> pd.DataFrame:
    """Создание тестовых метаданных."""
    return pd.DataFrame(
        {
            "ticker": tickers,
            "sector": ["Technology"] * len(tickers),
            "listing_date": ["2010-01-01"] * len(tickers),
            "currency": ["RUB"] * len(tickers),
        }
    )
