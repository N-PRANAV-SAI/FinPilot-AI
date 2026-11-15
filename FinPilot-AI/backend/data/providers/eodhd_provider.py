"""EODHD global financial market data provider adapter."""
import logging
import requests
import pandas as pd
from config.settings import settings
from backend.data.providers.base_provider import GlobalMarketDataProvider
from backend.data.providers.yfinance_provider import YFinanceProvider
from backend.data.global_exchanges import get_exchange_info, CURRENCY_SYMBOLS

log = logging.getLogger(__name__)


class EODHDProvider(GlobalMarketDataProvider):
    """EODHD API adapter for global stock exchanges with yfinance fallback."""

    BASE_URL = "https://eodhd.com/api"

    def __init__(self):
        self._fallback = YFinanceProvider()

    @property
    def name(self) -> str:
        return "EOD Historical Data (EODHD)"

    def is_available(self) -> bool:
        return bool(settings.eodhd_api_key and settings.eodhd_api_key.strip())

    def search_symbols(self, query: str, limit: int = 10) -> list[dict]:
        """Search global symbols via EODHD or fallback."""
        if not self.is_available():
            return self._fallback.search_symbols(query, limit)

        try:
            url = f"{self.BASE_URL}/search/{query}"
            r = requests.get(
                url,
                params={"api_token": settings.eodhd_api_key, "fmt": "json"},
                timeout=15,
            )
            r.raise_for_status()
            data = r.json()
            if not isinstance(data, list) or not data:
                return self._fallback.search_symbols(query, limit)

            results = []
            for item in data:
                code = item.get("Code")
                exchange = item.get("Exchange") or "US"
                if not code:
                    continue
                full_ticker = f"{code}.{exchange}" if exchange not in ("US", "") else code
                name = item.get("Name") or code
                currency = item.get("Currency") or "USD"
                country = item.get("Country") or "Unknown"
                exc_info = get_exchange_info(exchange)

                results.append({
                    "ticker": full_ticker,
                    "name": name,
                    "exchange": exchange,
                    "exchange_name": exc_info.name,
                    "country": country,
                    "region": exc_info.region,
                    "currency": currency,
                    "currency_symbol": CURRENCY_SYMBOLS.get(currency.upper(), currency),
                    "mic": exc_info.mic,
                    "instrument_type": item.get("Type", "Common Stock"),
                    "flag": exc_info.flag,
                    "provider": self.name,
                    "score": 1.0,
                })
                if len(results) >= limit:
                    break

            return results
        except Exception as exc:
            log.warning("EODHD search failed: %s. Falling back to yfinance.", exc)
            return self._fallback.search_symbols(query, limit)

    def fetch_history(self, ticker: str, period: str = "5y", interval: str = "1d") -> pd.DataFrame:
        """Fetch historical prices via EODHD or fallback."""
        if not self.is_available():
            return self._fallback.fetch_history(ticker, period, interval)

        try:
            url = f"{self.BASE_URL}/eod/{ticker}"
            r = requests.get(
                url,
                params={"api_token": settings.eodhd_api_key, "fmt": "json", "period": "d"},
                timeout=20,
            )
            r.raise_for_status()
            data = r.json()
            if not isinstance(data, list) or not data:
                return self._fallback.fetch_history(ticker, period, interval)

            df = pd.DataFrame(data)
            df["date"] = pd.to_datetime(df["date"])
            df = df.set_index("date").sort_index()
            df = df.rename(columns={
                "open": "Open",
                "high": "High",
                "low": "Low",
                "close": "Close",
                "adjusted_close": "Adj_Close",
                "volume": "Volume",
            })
            required = ["Open", "High", "Low", "Close", "Volume"]
            df = df[[c for c in required if c in df.columns]]
            if "Adj_Close" not in df.columns and "Close" in df.columns:
                df["Adj_Close"] = df["Close"]

            df = df[df["Close"] > 0].dropna(subset=["Close"])
            if len(df) < 60:
                return self._fallback.fetch_history(ticker, period, interval)

            log.info("Fetched %d rows for %s via EODHD.", len(df), ticker)
            return df
        except Exception as exc:
            log.warning("EODHD history fetch failed: %s. Falling back to yfinance.", exc)
            return self._fallback.fetch_history(ticker, period, interval)

    def fetch_fundamentals(self, ticker: str) -> dict:
        """Fetch fundamentals via EODHD or fallback."""
        if not self.is_available():
            return self._fallback.fetch_fundamentals(ticker)

        try:
            url = f"{self.BASE_URL}/fundamentals/{ticker}"
            r = requests.get(url, params={"api_token": settings.eodhd_api_key}, timeout=20)
            r.raise_for_status()
            data = r.json()
            gen = data.get("General", {})
            highlights = data.get("Highlights", {})
            curr = gen.get("CurrencyCode", "USD")
            exc = gen.get("Exchange", "US")
            exc_info = get_exchange_info(exc)

            return {
                "company_name": gen.get("Name") or ticker,
                "ticker": ticker,
                "exchange": exc,
                "country": gen.get("CountryName") or exc_info.country,
                "currency": curr,
                "currency_symbol": CURRENCY_SYMBOLS.get(curr.upper(), curr),
                "sector": gen.get("Sector"),
                "industry": gen.get("Industry"),
                "revenue": highlights.get("RevenueTTM"),
                "net_income": highlights.get("NetIncomeTTM"),
                "operating_income": highlights.get("OperatingIncomeTTM"),
                "total_assets": None,
                "total_liabilities": None,
                "total_debt": None,
                "operating_cash_flow": highlights.get("OperatingCashFlowTTM"),
                "revenue_growth": highlights.get("RevenueGrowth"),
                "profit_margin": highlights.get("ProfitMargin"),
                "eps": highlights.get("EarningsShare"),
                "debt_to_equity": None,
                "market_cap": highlights.get("MarketCapitalization"),
                "pe_ratio": highlights.get("PERatio"),
                "beta": gen.get("Beta"),
                "fifty_two_week_high": highlights.get("52WeekHigh"),
                "fifty_two_week_low": highlights.get("52WeekLow"),
                "website": gen.get("WebURL"),
                "description": gen.get("Description"),
                "reporting_currency": curr,
                "data_source": self.name,
            }
        except Exception as exc:
            log.warning("EODHD fundamentals failed: %s. Falling back to yfinance.", exc)
            return self._fallback.fetch_fundamentals(ticker)

    def get_supported_exchanges(self) -> list[dict]:
        return self._fallback.get_supported_exchanges()
