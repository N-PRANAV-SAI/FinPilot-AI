"""Unit and integration tests for FinPilot AI Fintech Analytics Engine."""
import pytest
import numpy as np
import pandas as pd

from backend.analytics.quant_research import compute_quant_metrics, compare_peer_assets
from backend.analytics.risk_analytics import compute_portfolio_risk_analytics
from backend.analytics.backtesting import run_backtest
from backend.analytics.data_quality import audit_ticker_data_quality, get_all_providers_health
from backend.analytics.screener import screen_stocks, compare_companies_side_by_side


def test_quant_metrics_calculation():
    """Verify quantitative research metrics computation."""
    res = compute_quant_metrics("NVDA", period="1y", benchmark_ticker="^GSPC")
    assert res["ticker"] == "NVDA"
    assert res["benchmark_ticker"] == "^GSPC"
    assert "cagr_pct" in res
    assert "historical_volatility_ann" in res
    assert "beta" in res
    assert "max_drawdown_pct" in res
    assert "sharpe_ratio" in res
    assert len(res["series"]["close"]) > 20
    assert len(res["series"]["rolling_vol_20d"]) > 20


def test_peer_asset_comparison():
    """Verify peer comparison and correlation matrix computation."""
    res = compare_peer_assets(["NVDA", "AAPL"], period="1y")
    assert "assets" in res
    assert "NVDA" in res["assets"]
    assert "AAPL" in res["assets"]
    assert "correlation_matrix" in res


def test_portfolio_risk_analytics_with_holdings():
    """Verify portfolio risk analytics with multi-asset holdings."""
    holdings = [
        {"ticker": "NVDA", "quantity": 10, "current_value": 15000.0},
        {"ticker": "AAPL", "quantity": 10, "current_value": 20000.0},
    ]
    res = compute_portfolio_risk_analytics(
        holdings=holdings,
        account_currency="INR",
        total_portfolio_value=50000.0,
        available_cash=15000.0,
    )
    assert not res["is_empty"]
    assert res["metrics"]["var_95_daily_pct"] > 0
    assert res["metrics"]["cvar_95_daily_pct"] >= res["metrics"]["var_95_daily_pct"]
    assert res["metrics"]["hhi_concentration"] > 0
    assert len(res["stress_tests"]) >= 3


def test_portfolio_risk_analytics_empty_cash():
    """Verify portfolio risk analytics handles 100% cash gracefully."""
    res = compute_portfolio_risk_analytics(
        holdings=[],
        account_currency="INR",
        total_portfolio_value=100000.0,
        available_cash=100000.0,
    )
    assert res["is_empty"]
    assert res["metrics"]["portfolio_volatility_ann_pct"] == 0.0
    assert res["metrics"]["var_95_daily_pct"] == 0.0


def test_backtest_moving_average_crossover():
    """Verify backtesting engine executes with anti-leakage safeguards."""
    res = run_backtest(
        ticker="NVDA",
        strategy_name="Moving Average Crossover",
        strategy_params={"fast_period": 10, "slow_period": 30},
        period="1y",
        initial_capital=100000.0,
    )
    assert res["ticker"] == "NVDA"
    assert res["initial_capital"] == 100000.0
    assert "final_capital" in res
    assert "cagr_pct" in res
    assert "max_drawdown_pct" in res
    assert len(res["series"]["equity"]) > 20
    assert len(res["anti_leakage_safeguards"]) == 4


def test_data_quality_audit():
    """Verify data quality auditor calculates integrity scores and freshness."""
    report = audit_ticker_data_quality("NVDA", period="1y")
    assert report["ticker"] == "NVDA"
    assert 0 <= report["quality_score"] <= 100
    assert report["freshness"] in ["LIVE", "CURRENT_EOD", "DELAYED", "SYNTHETIC_OFFLINE", "STALE"]
    assert "ohlcv_completeness_pct" in report["metrics"]


def test_providers_health():
    """Verify all external data providers have status entries."""
    health = get_all_providers_health()
    assert "yfinance" in health["providers"]
    assert "google_gemini" in health["providers"]
    assert "finnhub" in health["providers"]


def test_screener_and_comparison():
    """Verify stock screener and comparison engines."""
    matches = screen_stocks(sector="Technology", max_pe=100.0)
    assert isinstance(matches, list)

    comp = compare_companies_side_by_side(["NVDA", "AAPL"])
    assert len(comp["comparison_table"]) == 2
