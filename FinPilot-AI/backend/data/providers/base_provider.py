"""Abstract base class for global financial market data providers."""
from abc import ABC, abstractmethod
from typing import Any
import pandas as pd


class GlobalMarketDataProvider(ABC):
    """Abstract interface for all financial market data providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider identifier name."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check whether provider has necessary API keys and credentials."""
        pass

    @abstractmethod
    def search_symbols(self, query: str, limit: int = 10) -> list[dict]:
        """Search global symbols by company name or ticker.
        
        Returns list of standardized dicts:
        {
            "ticker": str,
            "name": str,
            "exchange": str,
            "country": str,
            "currency": str,
            "currency_symbol": str,
            "mic": str,
            "instrument_type": str,
            "provider": str,
            "score": float
        }
        """
        pass

    @abstractmethod
    def fetch_history(self, ticker: str, period: str = "5y", interval: str = "1d") -> pd.DataFrame:
        """Fetch historical OHLCV data.
        
        Returns clean DataFrame indexed by datetime with columns:
        Open, High, Low, Close, Adj_Close, Volume.
        """
        pass

    @abstractmethod
    def fetch_fundamentals(self, ticker: str) -> dict:
        """Fetch quarterly/annual fundamentals, valuation, and balance sheet metrics.
        
        Missing values remain None — never fabricated.
        """
        pass

    @abstractmethod
    def get_supported_exchanges(self) -> list[dict]:
        """Return list of supported global exchanges."""
        pass
