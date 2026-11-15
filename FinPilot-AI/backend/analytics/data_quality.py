"""FinPilot AI — Data Quality & Market Data Health Monitor.

Audits data provenance, freshness, completeness, gap anomalies, and provider health.
Never labels cached, synthetic, or delayed data as live.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd

from backend.data.market_data import fetch_market_data, get_latest_price, validate_ticker
from backend.data.providers.provider_factory import get_market_data_provider
from backend.data.providers.yfinance_provider import is_dns_online
from config.settings import settings

log = logging.getLogger(__name__)


def audit_ticker_data_quality(ticker: str, period: str = "1y") -> Dict[str, Any]:
    """Perform comprehensive data quality inspection on historical OHLCV data."""
    clean_ticker = validate_ticker(ticker)
    now_utc = datetime.now(timezone.utc)

    # 1. Fetch raw data
    provider = get_market_data_provider()
    online = is_dns_online()
    quote = get_latest_price(clean_ticker)

    df = fetch_market_data(clean_ticker, period=period)
    if df is None or df.empty:
        return {
            "ticker": clean_ticker,
            "status": "NO_DATA",
            "quality_score": 0.0,
            "provenance": "UNAVAILABLE",
            "freshness": "OFFLINE",
            "warnings": [f"No historical or live data could be retrieved for {clean_ticker}."],
        }

    total_bars = len(df)
    missing_closes = int(df["Close"].isna().sum()) if "Close" in df else 0
    missing_opens = int(df["Open"].isna().sum()) if "Open" in df else 0
    missing_highs = int(df["High"].isna().sum()) if "High" in df else 0
    missing_lows = int(df["Low"].isna().sum()) if "Low" in df else 0
    zero_volumes = int((df["Volume"] <= 0).sum()) if "Volume" in df else 0

    # Duplicate dates
    duplicate_dates = int(df.index.duplicated().sum())

    # Large single-day price gaps (>15%)
    close_series = df["Close"].astype(float)
    returns = close_series.pct_change().dropna()
    extreme_gaps = int((returns.abs() > 0.15).sum())

    # Latest bar date & freshness
    last_date = df.index[-1]
    if hasattr(last_date, "to_pydatetime"):
        last_dt = last_date.to_pydatetime()
        if last_dt.tzinfo is None:
            last_dt = last_dt.replace(tzinfo=timezone.utc)
    else:
        last_dt = now_utc

    age_days = (now_utc.date() - last_dt.date()).days

    # Freshness Classification
    quote_status = quote.get("quote_status", "UNKNOWN")
    is_live = quote.get("is_live", False) and online

    if is_live and age_days <= 1:
        freshness_label = "LIVE"
        freshness_color = "emerald"
    elif age_days <= 3:  # Weekend gap
        freshness_label = "CURRENT_EOD"
        freshness_color = "teal"
    elif age_days <= 7:
        freshness_label = "DELAYED"
        freshness_color = "amber"
    elif not online or quote.get("is_demo"):
        freshness_label = "SYNTHETIC_OFFLINE"
        freshness_color = "red"
    else:
        freshness_label = "STALE"
        freshness_color = "red"

    # Compute Quality Score (0 to 100)
    score = 100.0
    warnings = []

    if missing_closes > 0:
        penalty = min(missing_closes * 5, 25)
        score -= penalty
        warnings.append(f"{missing_closes} missing Close price records detected.")

    if zero_volumes > (total_bars * 0.05):
        score -= 10
        warnings.append(f"{zero_volumes} zero-volume trading sessions found ({zero_volumes/total_bars*100:.1f}%).")

    if duplicate_dates > 0:
        score -= 15
        warnings.append(f"{duplicate_dates} duplicate timestamp records detected.")

    if extreme_gaps > 3:
        warnings.append(f"{extreme_gaps} price gaps > 15% found (potential corporate split or dividend action).")

    if not online:
        score -= 20
        warnings.append("System running in offline isolation mode. Baseline benchmark cache active.")

    if age_days > 7 and online:
        score -= 25
        warnings.append(f"Data is {age_days} days behind real-time market.")

    quality_score = max(0.0, min(round(score, 1), 100.0))

    return {
        "ticker": clean_ticker,
        "checked_at": now_utc.isoformat(),
        "provider": provider.name,
        "is_online": online,
        "is_live": is_live,
        "provenance": quote.get("source", provider.name),
        "freshness": freshness_label,
        "freshness_color": freshness_color,
        "quality_score": quality_score,
        "total_records": total_bars,
        "date_range": {
            "start": str(df.index[0].date()) if hasattr(df.index[0], "date") else str(df.index[0]),
            "end": str(df.index[-1].date()) if hasattr(df.index[-1], "date") else str(df.index[-1]),
        },
        "days_since_latest_bar": age_days,
        "latest_price": quote.get("price"),
        "metrics": {
            "missing_ohlc_count": missing_closes + missing_opens + missing_highs + missing_lows,
            "zero_volume_count": zero_volumes,
            "duplicate_timestamps": duplicate_dates,
            "extreme_gaps_count": extreme_gaps,
            "ohlcv_completeness_pct": round(100.0 - ((missing_closes / total_bars) * 100), 2),
        },
        "warnings": warnings if warnings else ["All historical bars and quote records passed integrity validation."],
    }


def get_all_providers_health() -> Dict[str, Any]:
    """Audit system health and connectivity across all configured market and news APIs."""
    online = is_dns_online()
    now_utc = datetime.now(timezone.utc)

    providers = {
        "yfinance": {
            "name": "Yahoo Finance (Global)",
            "role": "Primary historical OHLCV & real-time quotes",
            "requires_key": False,
            "status": "ONLINE" if online else "OFFLINE_CACHE_ACTIVE",
            "color": "emerald" if online else "amber",
            "coverage": "US, India (NSE/BSE), Europe (LSE, DAX), Japan (TSE), Hong Kong",
        },
        "finnhub": {
            "name": "Finnhub Financial API",
            "role": "Financial News & Sentiment Analysis",
            "requires_key": True,
            "has_key": bool(settings.finnhub_api_key),
            "status": "CONNECTED" if (settings.finnhub_api_key and online) else "FALLBACK_ACTIVE",
            "color": "emerald" if (settings.finnhub_api_key and online) else "slate",
            "coverage": "Global corporate news & filings",
        },
        "google_gemini": {
            "name": "Google Gemini Generative AI",
            "role": "LLM Synthesis, Research Summaries & Co-Pilot",
            "requires_key": True,
            "has_key": bool(settings.gemini_api_key),
            "status": "CONNECTED" if (settings.gemini_api_key and online) else "LOCAL_QUANT_ACTIVE",
            "color": "emerald" if (settings.gemini_api_key and online) else "slate",
            "coverage": "Evidence-grounded quantitative reasoning",
        },
        "sec_edgar": {
            "name": "SEC EDGAR Disclosures",
            "role": "US 10-K & 10-Q Regulatory Filings",
            "requires_key": False,
            "status": "ONLINE" if online else "OFFLINE_ARCHIVE",
            "color": "emerald" if online else "amber",
            "coverage": "US Public Companies",
        },
    }

    return {
        "audited_at": now_utc.isoformat(),
        "network_online": online,
        "providers": providers,
    }
