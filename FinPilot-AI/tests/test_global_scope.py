"""Tests for Global Scope, Multi-Exchange, and Multi-Currency capabilities."""
import pytest
import pandas as pd
from backend.data.global_exchanges import (
    GLOBAL_EXCHANGES,
    get_exchange_info,
    format_currency_amount,
    normalize_ticker_for_exchange,
    CURRENCY_SYMBOLS,
)
from backend.data.company_search import search_global_companies, BENCHMARK_COMPANIES
from backend.data.providers.provider_factory import get_market_data_provider
from backend.data.providers.yfinance_provider import YFinanceProvider
from backend.data.providers.fmp_provider import FMPProvider
from backend.data.providers.eodhd_provider import EODHDProvider
from backend.data.filings_data import discover_company_documents
from backend.data.market_data import validate_ticker, get_latest_price
from backend.llm.explanation_generator import build_prompt


def test_global_exchanges_registry_coverage():
    """Verify key global exchanges are present in the registry."""
    required = ["NYSE", "NASDAQ", "NSE", "BSE", "LSE", "XETRA", "TSE", "HKEX", "ASX", "KRX", "SIX", "EURONEXT", "TADAWUL"]
    for code in required:
        assert code in GLOBAL_EXCHANGES, f"Missing exchange: {code}"
        exc = GLOBAL_EXCHANGES[code]
        assert exc.currency, f"Exchange {code} missing currency"
        assert exc.country, f"Exchange {code} missing country"


def test_exchange_resolution_from_suffixes():
    """Verify tickers with international suffixes resolve to the correct exchange and currency."""
    test_cases = [
        ("RELIANCE.NS", "NSE", "India", "INR", "₹"),
        ("TCS.BO", "BSE", "India", "INR", "₹"),
        ("7203.T", "TSE", "Japan", "JPY", "¥"),
        ("005930.KS", "KRX", "South Korea", "KRW", "₩"),
        ("SIE.DE", "XETRA", "Germany", "EUR", "€"),
        ("HSBA.L", "LSE", "United Kingdom", "GBP", "£"),
        ("BHP.AX", "ASX", "Australia", "AUD", "A$"),
        ("0700.HK", "HKEX", "Hong Kong", "HKD", "HK$"),
        ("NESN.SW", "SIX", "Switzerland", "CHF", "CHF"),
        ("2222.SR", "TADAWUL", "Saudi Arabia", "SAR", "SAR"),
        ("NVDA", "US", "United States", "USD", "$"),
    ]
    for ticker, expected_exc, expected_country, expected_curr, expected_sym in test_cases:
        info = get_exchange_info(ticker)
        assert info.country == expected_country, f"Expected {expected_country} for {ticker}, got {info.country}"
        assert info.currency == expected_curr, f"Expected {expected_curr} for {ticker}, got {info.currency}"
        assert info.currency_symbol == expected_sym, f"Expected {expected_sym} for {ticker}, got {info.currency_symbol}"


def test_native_currency_formatting():
    """Verify amounts format correctly in native currencies without hardcoded dollars."""
    assert format_currency_amount(1324.4, "INR") == "₹1,324.40 INR"
    assert format_currency_amount(2850.0, "JPY") == "¥2,850 JPY"
    assert format_currency_amount(75000.0, "KRW") == "₩75,000 KRW"
    assert format_currency_amount(178.67, "USD") == "$178.67 USD"
    assert format_currency_amount(155.20, "EUR") == "€155.20 EUR"
    assert format_currency_amount(650.50, "GBP") == "£650.50 GBP"


def test_ticker_validation_supports_international_formats():
    """Verify international ticker syntax is accepted."""
    valid_tickers = [
        "NVDA",
        "AAPL",
        "RELIANCE.NS",
        "TCS.NS",
        "7203.T",
        "005930.KS",
        "SIE.DE",
        "HSBA.L",
        "BHP.AX",
        "0700.HK",
        "NOVO-B.CO",
        "BRK-B",
        "2222.SR",
    ]
    for t in valid_tickers:
        assert validate_ticker(t) == t.upper()


def test_ticker_validation_rejects_invalids():
    """Verify dangerous or malformed strings are rejected."""
    with pytest.raises(ValueError):
        validate_ticker("")
    with pytest.raises(ValueError):
        validate_ticker("   ")
    with pytest.raises(ValueError):
        validate_ticker("DROP TABLE;--")


def test_global_company_search_by_name():
    """Verify search engine finds international companies by name."""
    queries = ["Reliance", "Toyota", "Siemens", "Samsung", "Sony", "Apple"]
    for q in queries:
        results = search_global_companies(q, limit=5)
        assert len(results) > 0, f"Search failed for query '{q}'"
        assert any(q.lower() in r["name"].lower() or q.lower() in r["ticker"].lower() for r in results)


def test_global_company_search_with_country_filter():
    """Verify search filter restricts results to specified jurisdiction."""
    results_india = search_global_companies("Reliance", country_filter="India", limit=5)
    for r in results_india:
        assert r["country"] == "India"

    results_japan = search_global_companies("Toyota", country_filter="Japan", limit=5)
    for r in results_japan:
        assert r["country"] == "Japan"


def test_provider_factory_and_adapters():
    """Verify market data provider hierarchy and fallback mechanics."""
    provider = get_market_data_provider()
    assert provider is not None
    assert provider.name

    # Test FMP adapter fallback instantiation
    fmp = FMPProvider()
    assert fmp.name == "Financial Modeling Prep (FMP)"

    # Test EODHD adapter fallback instantiation
    eod = EODHDProvider()
    assert eod.name == "EOD Historical Data (EODHD)"


def test_country_aware_filing_discovery():
    """Verify regulatory discovery routes appropriately by country."""
    # US company
    us_filings = discover_company_documents("AAPL", company_name="Apple Inc.", country="United States", limit=3)
    assert len(us_filings) > 0
    assert any("SEC" in f["document_type"] or "sec.gov" in f.get("url", "") for f in us_filings)

    # Indian company
    in_filings = discover_company_documents("RELIANCE.NS", company_name="Reliance Industries", country="India", exchange="NSE", limit=2)
    assert len(in_filings) > 0
    assert any("NSE" in f["source"] or "India" in f["country"] for f in in_filings)

    # German company
    de_filings = discover_company_documents("SIE.DE", company_name="Siemens AG", country="Germany", exchange="XETRA", limit=2)
    assert len(de_filings) > 0
    assert any("Germany" in f["country"] for f in de_filings)


def test_llm_prompt_incorporates_global_metadata():
    """Verify LLM prompt is dynamically adapted for foreign asset, currency, and exchange without US hardcoding."""
    prompt = build_prompt(
        ticker="RELIANCE.NS",
        prediction={"direction": "Positive", "probability": 0.72, "selected_model": "Random Forest"},
        sentiment={"available": True, "overall_label": "Positive", "score": 0.45},
        evidence=[{"text": "Refining margins improved by 12%.", "metadata": {"document_title": "Annual Report"}}],
        shap_info={"top_positive": [{"feature": "rsi14", "contribution": 0.25}]},
        fundamentals={
            "company_name": "Reliance Industries Limited",
            "country": "India",
            "exchange": "NSE",
            "currency": "INR",
        },
    )
    assert "Reliance Industries Limited" in prompt
    assert "RELIANCE.NS" in prompt
    assert "NSE" in prompt
    assert "India" in prompt
    assert "INR" in prompt
    assert "5-exchange-trading-day" in prompt.lower()
