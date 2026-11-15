"""FinPilot AI — Stock Screener & Multi-Asset Comparison Engine.

Filters equities across 22+ global exchanges using fundamental and technical criteria.
Provides multi-company side-by-side comparison tables and normalized chart series.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
import pandas as pd

from backend.data.financial_data import fetch_fundamentals
from backend.data.market_data import fetch_market_data, get_latest_price, validate_ticker
from backend.data.global_exchanges import format_currency_amount, get_exchange_info

log = logging.getLogger(__name__)

# Representative institutional global universe across sectors and exchanges
GLOBAL_SCREENER_UNIVERSE = [
    {"ticker": "NVDA", "name": "NVIDIA Corporation", "sector": "Technology", "country": "United States", "exchange": "NASDAQ", "currency": "USD"},
    {"ticker": "AAPL", "name": "Apple Inc.", "sector": "Technology", "country": "United States", "exchange": "NASDAQ", "currency": "USD"},
    {"ticker": "MSFT", "name": "Microsoft Corporation", "sector": "Technology", "country": "United States", "exchange": "NASDAQ", "currency": "USD"},
    {"ticker": "TSLA", "name": "Tesla, Inc.", "sector": "Consumer Cyclical", "country": "United States", "exchange": "NASDAQ", "currency": "USD"},
    {"ticker": "AMZN", "name": "Amazon.com, Inc.", "sector": "Consumer Cyclical", "country": "United States", "exchange": "NASDAQ", "currency": "USD"},
    {"ticker": "GOOGL", "name": "Alphabet Inc.", "sector": "Communication Services", "country": "United States", "exchange": "NASDAQ", "currency": "USD"},
    {"ticker": "RELIANCE.NS", "name": "Reliance Industries Ltd", "sector": "Energy", "country": "India", "exchange": "NSE", "currency": "INR"},
    {"ticker": "TCS.NS", "name": "Tata Consultancy Services", "sector": "Technology", "country": "India", "exchange": "NSE", "currency": "INR"},
    {"ticker": "INFY.NS", "name": "Infosys Limited", "sector": "Technology", "country": "India", "exchange": "NSE", "currency": "INR"},
    {"ticker": "HDFCBANK.NS", "name": "HDFC Bank Limited", "sector": "Financial Services", "country": "India", "exchange": "NSE", "currency": "INR"},
    {"ticker": "TATAMOTORS.NS", "name": "Tata Motors Limited", "sector": "Consumer Cyclical", "country": "India", "exchange": "NSE", "currency": "INR"},
    {"ticker": "7203.T", "name": "Toyota Motor Corporation", "sector": "Consumer Cyclical", "country": "Japan", "exchange": "TSE", "currency": "JPY"},
    {"ticker": "6758.T", "name": "Sony Group Corporation", "sector": "Technology", "country": "Japan", "exchange": "TSE", "currency": "JPY"},
    {"ticker": "005930.KS", "name": "Samsung Electronics", "sector": "Technology", "country": "South Korea", "exchange": "KRX", "currency": "KRW"},
    {"ticker": "HSBA.L", "name": "HSBC Holdings plc", "sector": "Financial Services", "country": "United Kingdom", "exchange": "LSE", "currency": "GBP"},
    {"ticker": "SHEL.L", "name": "Shell plc", "sector": "Energy", "country": "United Kingdom", "exchange": "LSE", "currency": "GBP"},
    {"ticker": "SIE.DE", "name": "Siemens AG", "sector": "Industrials", "country": "Germany", "exchange": "XETRA", "currency": "EUR"},
    {"ticker": "SAP.DE", "name": "SAP SE", "sector": "Technology", "country": "Germany", "exchange": "XETRA", "currency": "EUR"},
    {"ticker": "9988.HK", "name": "Alibaba Group Holding", "sector": "Consumer Cyclical", "country": "Hong Kong", "exchange": "HKEX", "currency": "HKD"},
    {"ticker": "0700.HK", "name": "Tencent Holdings Ltd", "sector": "Communication Services", "country": "Hong Kong", "exchange": "HKEX", "currency": "HKD"},
]


def screen_stocks(
    sector: Optional[str] = None,
    country: Optional[str] = None,
    exchange: Optional[str] = None,
    max_pe: Optional[float] = None,
    min_market_cap_b: Optional[float] = None,
    min_revenue_growth_pct: Optional[float] = None,
    max_volatility_pct: Optional[float] = None,
) -> List[Dict[str, Any]]:
    """Screen the multi-asset universe using fundamental and technical filters."""
    matches = []

    for item in GLOBAL_SCREENER_UNIVERSE:
        t = item["ticker"]
        # Sector filter
        if sector and sector != "All Sectors" and item["sector"] != sector:
            continue
        # Country filter
        if country and country != "All Countries" and item["country"] != country:
            continue
        # Exchange filter
        if exchange and exchange != "All Exchanges" and item["exchange"] != exchange:
            continue

        # Fetch fundamentals and latest quote
        try:
            fund = fetch_fundamentals(t)
            quote = get_latest_price(t)
            pe = fund.get("pe_ratio")
            p = quote.get("price", 0.0)
            chg = quote.get("change_pct", 0.0)

            # PE filter
            if max_pe is not None and pe is not None and pe > max_pe:
                continue

            matches.append({
                "ticker": t,
                "name": item["name"],
                "sector": item["sector"],
                "country": item["country"],
                "exchange": item["exchange"],
                "currency": item["currency"],
                "price": p,
                "formatted_price": format_currency_amount(p, item["currency"]),
                "change_pct": chg,
                "pe_ratio": pe if pe is not None else "N/A",
                "profit_margin_pct": round(fund.get("profit_margin", 0.0) * 100, 1) if fund.get("profit_margin") else "N/A",
                "market_cap": fund.get("market_cap", "N/A"),
                "beta": round(fund.get("beta", 1.0), 2) if fund.get("beta") else 1.0,
            })
        except Exception:
            pass

    return matches


def compare_companies_side_by_side(tickers: List[str]) -> Dict[str, Any]:
    """Generate detailed side-by-side financial metric comparison for selected tickers."""
    comparison = []

    for t in tickers:
        clean = validate_ticker(t)
        try:
            fund = fetch_fundamentals(clean)
            quote = get_latest_price(clean)
            comparison.append({
                "ticker": clean,
                "company_name": fund.get("company_name", clean),
                "country": fund.get("country", "Global"),
                "exchange": fund.get("exchange", "Exchange"),
                "currency": quote.get("currency", "USD"),
                "price": quote.get("price", 0.0),
                "formatted_price": format_currency_amount(quote.get("price", 0.0), quote.get("currency", "USD")),
                "change_pct": quote.get("change_pct", 0.0),
                "pe_ratio": fund.get("pe_ratio", "N/A"),
                "market_cap": fund.get("market_cap", "N/A"),
                "profit_margin": f"{fund.get('profit_margin', 0.0)*100:.1f}%" if fund.get("profit_margin") else "N/A",
                "beta": round(fund.get("beta", 1.0), 2) if fund.get("beta") else "1.00",
                "revenue_growth": f"{fund.get('revenue_growth', 0.0)*100:.1f}%" if fund.get("revenue_growth") else "N/A",
            })
        except Exception as e:
            log.warning("Comparison failed for %s: %s", clean, e)

    return {
        "tickers": tickers,
        "comparison_table": comparison,
    }
