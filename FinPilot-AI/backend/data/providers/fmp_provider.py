"""Financial Modeling Prep (FMP) global data provider adapter."""
import logging
import requests
import pandas as pd
from config.settings import settings
from backend.data.providers.base_provider import GlobalMarketDataProvider
from backend.data.providers.yfinance_provider import YFinanceProvider
from backend.data.global_exchanges import get_exchange_info, CURRENCY_SYMBOLS

log = logging.getLogger(__name__)


class FMPProvider(GlobalMarketDataProvider):
    """Financial Modeling Prep (FMP) API adapter with fallback to Yahoo Finance."""

    BASE_URL = "https://financialmodelingprep.com/api/v3"

    def __init__(self):
        self._fallback = YFinanceProvider()

    @property
    def name(self) -> str:
        return "Financial Modeling Prep (FMP)"

    def is_available(self) -> bool:
        return bool(settings.fmp_api_key and settings.fmp_api_key.strip())

    def search_symbols(self, query: str, limit: int = 10) -> list[dict]:
        """Search global symbols via FMP endpoint, or cascade to fallback."""
        if not self.is_available():
            return self._fallback.search_symbols(query, limit)

        try:
            url = f"{self.BASE_URL}/search"
            r = requests.get(
                url,
                params={"query": query, "limit": limit * 2, "apikey": settings.fmp_api_key},
                timeout=15,
            )
            r.raise_for_status()
            data = r.json()
            if not isinstance(data, list) or not data:
                return self._fallback.search_symbols(query, limit)

            results = []
            for item in data:
                symbol = item.get("symbol")
                if not symbol:
                    continue
                name = item.get("name") or symbol
                currency = item.get("currency") or "USD"
                exchange = item.get("exchangeShortName") or "US"
                exc_info = get_exchange_info(exchange)

                results.append({
                    "ticker": symbol,
                    "name": name,
                    "exchange": exchange,
                    "exchange_name": exc_info.name,
                    "country": exc_info.country,
                    "region": exc_info.region,
                    "currency": currency,
                    "currency_symbol": CURRENCY_SYMBOLS.get(currency.upper(), currency),
                    "mic": exc_info.mic,
                    "instrument_type": "EQUITY",
                    "flag": exc_info.flag,
                    "provider": self.name,
                    "score": 1.0,
                })
                if len(results) >= limit:
                    break

            return results
        except Exception as exc:
            log.warning("FMP search failed for '%s': %s. Falling back to yfinance.", query, exc)
            return self._fallback.search_symbols(query, limit)

    def fetch_history(self, ticker: str, period: str = "5y", interval: str = "1d") -> pd.DataFrame:
        """Fetch historical prices via FMP or cascade to fallback."""
        if not self.is_available():
            return self._fallback.fetch_history(ticker, period, interval)

        try:
            url = f"{self.BASE_URL}/historical-price-full/{ticker}"
            r = requests.get(url, params={"apikey": settings.fmp_api_key}, timeout=20)
            r.raise_for_status()
            payload = r.json()
            hist = payload.get("historical", [])
            if not hist:
                return self._fallback.fetch_history(ticker, period, interval)

            df = pd.DataFrame(hist)
            df["date"] = pd.to_datetime(df["date"])
            df = df.set_index("date").sort_index()
            df = df.rename(columns={
                "open": "Open",
                "high": "High",
                "low": "Low",
                "close": "Close",
                "adjClose": "Adj_Close",
                "volume": "Volume",
            })
            required = ["Open", "High", "Low", "Close", "Volume"]
            df = df[[c for c in required if c in df.columns]]
            if "Adj_Close" not in df.columns and "Close" in df.columns:
                df["Adj_Close"] = df["Close"]

            df = df[df["Close"] > 0].dropna(subset=["Close"])
            if len(df) < 60:
                return self._fallback.fetch_history(ticker, period, interval)

            log.info("Fetched %d rows for %s via FMP.", len(df), ticker)
            return df
        except Exception as exc:
            log.warning("FMP history fetch failed for %s: %s. Falling back to yfinance.", ticker, exc)
            return self._fallback.fetch_history(ticker, period, interval)

    def fetch_fundamentals(self, ticker: str) -> dict:
        """Fetch fundamentals via FMP or cascade to fallback."""
        if not self.is_available():
            return self._fallback.fetch_fundamentals(ticker)

        try:
            url = f"{self.BASE_URL}/profile/{ticker}"
            r = requests.get(url, params={"apikey": settings.fmp_api_key}, timeout=15)
            r.raise_for_status()
            profiles = r.json()
            if not profiles or not isinstance(profiles, list):
                return self._fallback.fetch_fundamentals(ticker)

            p = profiles[0]
            curr = p.get("currency") or "USD"
            exc = p.get("exchangeShortName") or "US"
            exc_info = get_exchange_info(exc)

            return {
                "company_name": p.get("companyName") or ticker,
                "ticker": ticker,
                "exchange": exc,
                "country": p.get("country") or exc_info.country,
                "currency": curr,
                "currency_symbol": CURRENCY_SYMBOLS.get(curr.upper(), curr),
                "sector": p.get("sector"),
                "industry": p.get("industry"),
                "revenue": None,
                "net_income": None,
                "operating_income": None,
                "total_assets": None,
                "total_liabilities": None,
                "total_debt": None,
                "operating_cash_flow": None,
                "revenue_growth": None,
                "profit_margin": None,
                "eps": p.get("eps"),
                "debt_to_equity": None,
                "market_cap": p.get("mktCap"),
                "pe_ratio": None,
                "beta": p.get("beta"),
                "fifty_two_week_high": None,
                "fifty_two_week_low": None,
                "website": p.get("website"),
                "description": p.get("description"),
                "reporting_currency": curr,
                "data_source": self.name,
            }
        except Exception as exc:
            log.warning("FMP profile fetch failed for %s: %s. Falling back to yfinance.", ticker, exc)
            return self._fallback.fetch_fundamentals(ticker)

    def get_supported_exchanges(self) -> list[dict]:
        return self._fallback.get_supported_exchanges()
