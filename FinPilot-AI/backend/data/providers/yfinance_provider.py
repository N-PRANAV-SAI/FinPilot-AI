"""Global market data provider implementation using yfinance."""
import logging
import pandas as pd
import yfinance as yf
from backend.data.providers.base_provider import GlobalMarketDataProvider
from backend.data.global_exchanges import (
    GLOBAL_EXCHANGES,
    get_exchange_info,
    CURRENCY_SYMBOLS,
)

log = logging.getLogger(__name__)

_DNS_ONLINE = None

def is_dns_online() -> bool:
    global _DNS_ONLINE
    if _DNS_ONLINE is not None:
        return _DNS_ONLINE
    try:
        import socket
        socket.gethostbyname("dns.google")
        _DNS_ONLINE = True
    except Exception:
        _DNS_ONLINE = False
    return _DNS_ONLINE


class YFinanceProvider(GlobalMarketDataProvider):
    """Yahoo Finance provider offering zero-config universal global coverage."""

    @property
    def name(self) -> str:
        return "Yahoo Finance"

    def is_available(self) -> bool:
        return True  # Zero-config public endpoints always available

    def search_symbols(self, query: str, limit: int = 10) -> list[dict]:
        """Search global symbols by company name, ticker, or partial text."""
        query = query.strip()
        if not query or not is_dns_online():
            return []

        try:
            s = yf.Search(query, max_results=max(limit * 2, 10))
            quotes = getattr(s, "quotes", []) or []
            results = []

            for q in quotes:
                symbol = q.get("symbol")
                if not symbol:
                    continue

                shortname = q.get("shortname") or q.get("longname") or symbol
                exchange_raw = q.get("exchange") or ""
                quote_type = q.get("quoteType") or "EQUITY"

                # Filter out crypto/indices/currencies if user is searching for equities
                if quote_type not in ("EQUITY", "ETF", "MUTUALFUND"):
                    continue

                exc_info = get_exchange_info(exchange_raw or symbol)
                currency = exc_info.currency
                currency_symbol = exc_info.currency_symbol

                results.append({
                    "ticker": symbol,
                    "name": shortname,
                    "exchange": exc_info.code,
                    "exchange_name": exc_info.name,
                    "country": exc_info.country,
                    "region": exc_info.region,
                    "currency": currency,
                    "currency_symbol": currency_symbol,
                    "mic": exc_info.mic,
                    "instrument_type": quote_type,
                    "flag": exc_info.flag,
                    "provider": self.name,
                    "score": float(q.get("score", 1.0)),
                })

                if len(results) >= limit:
                    break

            log.info("YFinance search for '%s' returned %d symbols.", query, len(results))
            return results
        except Exception as exc:
            log.warning("YFinance search failed for '%s': %s", query, exc)
            return []

    def fetch_history(self, ticker: str, period: str = "5y", interval: str = "1d") -> pd.DataFrame:
        """Fetch historical OHLCV data."""
        if not is_dns_online():
            raise RuntimeError(f"Network is offline. Using local market baseline for {ticker}.")
        ticker = ticker.strip().upper()
        try:
            data = yf.download(
                ticker,
                period=period,
                interval=interval,
                auto_adjust=False,
                progress=False,
                threads=False,
            )
            if data is None or data.empty:
                raise ValueError(f"No market history returned for {ticker}. Check the ticker or try again.")

            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.get_level_values(0)

            data = data.rename(columns={"Adj Close": "Adj_Close"})
            required = ["Open", "High", "Low", "Close", "Volume"]
            missing = [c for c in required if c not in data.columns]
            if missing:
                raise ValueError(f"Provider omitted required fields: {missing}")

            data.index = pd.to_datetime(data.index).tz_localize(None)
            data = data[~data.index.duplicated(keep="last")].sort_index()
            data = data.dropna(subset=["Close"])
            data = data[data["Close"] > 0]

            if len(data) < 60:
                raise ValueError(f"Only {len(data)} trading days available for {ticker}. Minimum required: 60.")

            log.info("Fetched %d rows of market data for %s via %s", len(data), ticker, self.name)
            return data
        except Exception as exc:
            log.warning("YFinance history download failed for %s: %s", ticker, exc)
            raise

    def fetch_fundamentals(self, ticker: str) -> dict:
        """Fetch comprehensive financial statements, ratios, and profile."""
        if not is_dns_online():
            raise RuntimeError(f"Network is offline. Using local financial baseline for {ticker}.")
        ticker = ticker.strip().upper()
        exc_info = get_exchange_info(ticker)
        default_currency = exc_info.currency

        try:
            t = yf.Ticker(ticker)
            info = t.info or {}

            # Statements extraction
            financials = getattr(t, "financials", None)
            balance_sheet = getattr(t, "balance_sheet", None)
            cash_flow = getattr(t, "cashflow", None)

            def _get_val(df, row_name):
                if df is not None and not df.empty and row_name in df.index:
                    series = df.loc[row_name].dropna()
                    if not series.empty:
                        return float(series.iloc[0])
                return None

            rev = _get_val(financials, "Total Revenue") or info.get("totalRevenue")
            net_inc = _get_val(financials, "Net Income") or info.get("netIncomeToCommon")
            op_inc = _get_val(financials, "Operating Income") or info.get("operatingIncome")
            tot_assets = _get_val(balance_sheet, "Total Assets")
            tot_liab = _get_val(balance_sheet, "Total Liabilities Net Minority Interest")
            tot_debt = _get_val(balance_sheet, "Total Debt") or info.get("totalDebt")
            cflow = _get_val(cash_flow, "Operating Cash Flow") or info.get("operatingCashflow")

            currency = info.get("currency") or default_currency
            symbol_curr = CURRENCY_SYMBOLS.get(currency.upper(), currency)

            return {
                "company_name": info.get("longName") or info.get("shortName") or ticker,
                "ticker": ticker,
                "exchange": info.get("exchange") or exc_info.code,
                "country": info.get("country") or exc_info.country,
                "currency": currency,
                "currency_symbol": symbol_curr,
                "sector": info.get("sector"),
                "industry": info.get("industry"),
                "revenue": rev,
                "net_income": net_inc,
                "operating_income": op_inc,
                "total_assets": tot_assets,
                "total_liabilities": tot_liab,
                "total_debt": tot_debt,
                "operating_cash_flow": cflow,
                "revenue_growth": info.get("revenueGrowth"),
                "profit_margin": info.get("profitMargins"),
                "operating_margins": info.get("operatingMargins"),
                "eps": info.get("trailingEps"),
                "forward_eps": info.get("forwardEps"),
                "debt_to_equity": info.get("debtToEquity"),
                "market_cap": info.get("marketCap"),
                "enterprise_value": info.get("enterpriseValue"),
                "pe_ratio": info.get("trailingPE"),
                "forward_pe": info.get("forwardPE"),
                "price_to_book": info.get("priceToBook"),
                "dividend_yield": info.get("dividendYield"),
                "beta": info.get("beta"),
                "fifty_two_week_high": info.get("fiftyTwoWeekHigh"),
                "fifty_two_week_low": info.get("fiftyTwoWeekLow"),
                "website": info.get("website"),
                "description": info.get("longBusinessSummary"),
                "reporting_currency": currency,
                "data_source": self.name,
            }
        except Exception as exc:
            log.warning("YFinance fundamentals extraction failed for %s: %s", ticker, exc)
            return {
                "company_name": ticker,
                "ticker": ticker,
                "exchange": exc_info.code,
                "country": exc_info.country,
                "currency": default_currency,
                "currency_symbol": exc_info.currency_symbol,
                "sector": None,
                "industry": None,
                "revenue": None,
                "net_income": None,
                "operating_income": None,
                "total_assets": None,
                "total_liabilities": None,
                "total_debt": None,
                "operating_cash_flow": None,
                "revenue_growth": None,
                "profit_margin": None,
                "eps": None,
                "debt_to_equity": None,
                "market_cap": None,
                "reporting_currency": default_currency,
                "data_source": self.name,
            }

    def get_supported_exchanges(self) -> list[dict]:
        return [
            {
                "code": exc.code,
                "name": exc.name,
                "country": exc.country,
                "currency": exc.currency,
                "mic": exc.mic,
                "suffix": exc.suffix,
                "flag": exc.flag,
            }
            for exc in GLOBAL_EXCHANGES.values()
        ]
