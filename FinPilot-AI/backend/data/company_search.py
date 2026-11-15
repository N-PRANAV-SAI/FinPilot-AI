"""Universal Global Company Search Engine."""
import logging
from typing import List, Dict, Any
from backend.data.providers.provider_factory import get_market_data_provider
from backend.data.global_exchanges import (
    GLOBAL_EXCHANGES,
    get_exchange_info,
    normalize_ticker_for_exchange,
    CURRENCY_SYMBOLS,
)

log = logging.getLogger(__name__)

# Curated global benchmark directory for instantaneous lookups
BENCHMARK_COMPANIES = [
    # United States
    {"ticker": "NVDA", "name": "NVIDIA Corporation", "exchange": "NASDAQ", "country": "United States", "currency": "USD", "sector": "Technology"},
    {"ticker": "AAPL", "name": "Apple Inc.", "exchange": "NASDAQ", "country": "United States", "currency": "USD", "sector": "Technology"},
    {"ticker": "MSFT", "name": "Microsoft Corporation", "exchange": "NASDAQ", "country": "United States", "currency": "USD", "sector": "Technology"},
    {"ticker": "TSLA", "name": "Tesla, Inc.", "exchange": "NASDAQ", "country": "United States", "currency": "USD", "sector": "Consumer Cyclical"},
    {"ticker": "AMZN", "name": "Amazon.com, Inc.", "exchange": "NASDAQ", "country": "United States", "currency": "USD", "sector": "Consumer Cyclical"},
    {"ticker": "GOOGL", "name": "Alphabet Inc.", "exchange": "NASDAQ", "country": "United States", "currency": "USD", "sector": "Communication Services"},
    
    # India
    {"ticker": "RELIANCE.NS", "name": "Reliance Industries Limited", "exchange": "NSE", "country": "India", "currency": "INR", "sector": "Energy"},
    {"ticker": "TCS.NS", "name": "Tata Consultancy Services Limited", "exchange": "NSE", "country": "India", "currency": "INR", "sector": "Technology"},
    {"ticker": "INFY.NS", "name": "Infosys Limited", "exchange": "NSE", "country": "India", "currency": "INR", "sector": "Technology"},
    {"ticker": "HDFCBANK.NS", "name": "HDFC Bank Limited", "exchange": "NSE", "country": "India", "currency": "INR", "sector": "Financial Services"},
    {"ticker": "TATAMOTORS.NS", "name": "Tata Motors Limited", "exchange": "NSE", "country": "India", "currency": "INR", "sector": "Consumer Cyclical"},
    
    # Japan
    {"ticker": "7203.T", "name": "Toyota Motor Corporation", "exchange": "TSE", "country": "Japan", "currency": "JPY", "sector": "Consumer Cyclical"},
    {"ticker": "6758.T", "name": "Sony Group Corporation", "exchange": "TSE", "country": "Japan", "currency": "JPY", "sector": "Technology"},
    {"ticker": "9984.T", "name": "SoftBank Group Corp.", "exchange": "TSE", "country": "Japan", "currency": "JPY", "sector": "Communication Services"},
    
    # South Korea
    {"ticker": "005930.KS", "name": "Samsung Electronics Co., Ltd.", "exchange": "KRX", "country": "South Korea", "currency": "KRW", "sector": "Technology"},
    {"ticker": "000660.KS", "name": "SK Hynix Inc.", "exchange": "KRX", "country": "South Korea", "currency": "KRW", "sector": "Technology"},
    
    # United Kingdom
    {"ticker": "HSBA.L", "name": "HSBC Holdings plc", "exchange": "LSE", "country": "United Kingdom", "currency": "GBP", "sector": "Financial Services"},
    {"ticker": "SHEL.L", "name": "Shell plc", "exchange": "LSE", "country": "United Kingdom", "currency": "GBP", "sector": "Energy"},
    {"ticker": "AZN.L", "name": "AstraZeneca PLC", "exchange": "LSE", "country": "United Kingdom", "currency": "GBP", "sector": "Healthcare"},
    
    # Germany
    {"ticker": "SIE.DE", "name": "Siemens AG", "exchange": "XETRA", "country": "Germany", "currency": "EUR", "sector": "Industrials"},
    {"ticker": "SAP.DE", "name": "SAP SE", "exchange": "XETRA", "country": "Germany", "currency": "EUR", "sector": "Technology"},
    {"ticker": "BMW.DE", "name": "Bayerische Motoren Werke AG (BMW)", "exchange": "XETRA", "country": "Germany", "currency": "EUR", "sector": "Consumer Cyclical"},
    
    # China & Hong Kong
    {"ticker": "0700.HK", "name": "Tencent Holdings Limited", "exchange": "HKEX", "country": "Hong Kong", "currency": "HKD", "sector": "Communication Services"},
    {"ticker": "9988.HK", "name": "Alibaba Group Holding Limited", "exchange": "HKEX", "country": "Hong Kong", "currency": "HKD", "sector": "Consumer Cyclical"},
    
    # Australia
    {"ticker": "BHP.AX", "name": "BHP Group Limited", "exchange": "ASX", "country": "Australia", "currency": "AUD", "sector": "Basic Materials"},
    {"ticker": "CBA.AX", "name": "Commonwealth Bank of Australia", "exchange": "ASX", "country": "Australia", "currency": "AUD", "sector": "Financial Services"},
    
    # Europe
    {"ticker": "NESN.SW", "name": "Nestlé S.A.", "exchange": "SIX", "country": "Switzerland", "currency": "CHF", "sector": "Consumer Defensive"},
    {"ticker": "NOVO-B.CO", "name": "Novo Nordisk A/S", "exchange": "CSE", "country": "Denmark", "currency": "DKK", "sector": "Healthcare"},
    {"ticker": "MC.PA", "name": "LVMH Moët Hennessy Louis Vuitton", "exchange": "EURONEXT", "country": "France", "currency": "EUR", "sector": "Consumer Cyclical"},
    {"ticker": "ASML.AS", "name": "ASML Holding N.V.", "exchange": "AMS", "country": "Netherlands", "currency": "EUR", "sector": "Technology"},
    
    # Canada
    {"ticker": "RY.TO", "name": "Royal Bank of Canada", "exchange": "TSX", "country": "Canada", "currency": "CAD", "sector": "Financial Services"},
    {"ticker": "SHOP.TO", "name": "Shopify Inc.", "exchange": "TSX", "country": "Canada", "currency": "CAD", "sector": "Technology"},
    
    # Saudi Arabia
    {"ticker": "2222.SR", "name": "Saudi Arabian Oil Company (Saudi Aramco)", "exchange": "TADAWUL", "country": "Saudi Arabia", "currency": "SAR", "sector": "Energy"},
]


def search_global_companies(
    query: str,
    country_filter: str | None = None,
    exchange_filter: str | None = None,
    limit: int = 12,
) -> List[Dict[str, Any]]:
    """Universal company search engine across global stock exchanges.
    
    1. Checks local benchmark index for instant zero-latency match.
    2. Queries active provider dynamic search API.
    3. Standardizes result fields, currency symbols, and exchange flags.
    4. Filters by country or exchange if specified.
    """
    query = (query or "").strip()
    if not query:
        return []

    q_lower = query.lower()
    results = []
    seen_tickers = set()

    # Step 1: Check curated benchmarks for instant exact/substring hits
    for item in BENCHMARK_COMPANIES:
        t = item["ticker"]
        n = item["name"]
        exc = item["exchange"]
        cntry = item["country"]
        
        matches = (
            q_lower in t.lower()
            or q_lower in n.lower()
            or q_lower in exc.lower()
            or q_lower in cntry.lower()
        )
        if matches:
            if country_filter and country_filter.lower() not in cntry.lower():
                continue
            if exchange_filter and exchange_filter.upper() != exc.upper():
                continue

            info = get_exchange_info(exc)
            results.append({
                "ticker": t,
                "name": n,
                "exchange": exc,
                "exchange_name": info.name,
                "country": cntry,
                "region": info.region,
                "currency": item["currency"],
                "currency_symbol": CURRENCY_SYMBOLS.get(item["currency"], item["currency"]),
                "mic": info.mic,
                "instrument_type": "EQUITY",
                "flag": info.flag,
                "provider": "Global Verified Directory",
                "score": 10.0 if (q_lower == t.lower() or q_lower == n.lower()) else 5.0,
            })
            seen_tickers.add(t.upper())

    # Step 2: Query active market data provider dynamic search
    try:
        provider = get_market_data_provider()
        provider_matches = provider.search_symbols(query, limit=limit)

        for m in provider_matches:
            t = m["ticker"].upper()
            if t in seen_tickers:
                continue

            cntry = m.get("country", "")
            exc = m.get("exchange", "")

            if country_filter and country_filter.lower() not in cntry.lower():
                continue
            if exchange_filter and exchange_filter.upper() != exc.upper():
                continue

            results.append(m)
            seen_tickers.add(t)

    except Exception as exc:
        log.warning("Dynamic provider search failed for '%s': %s", query, exc)

    # Sort results: exact ticker/name matches first
    def _rank(r):
        t_match = 0 if r["ticker"].lower() == q_lower else 1
        n_match = 0 if q_lower in r["name"].lower() else 1
        return (t_match, n_match, -r.get("score", 0.0))

    results.sort(key=_rank)
    return results[:limit]


# Backward compatibility alias
search_companies = search_global_companies

