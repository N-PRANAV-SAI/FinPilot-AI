"""FinPilot AI — Quantitative Research Lab Analytics Engine.

Provides institutional-grade return analytics, risk metrics, and comparative analysis.
All calculations use strictly historical data with zero look-ahead bias.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from scipy import stats

from backend.data.market_data import fetch_market_data, get_latest_price, validate_ticker
from backend.preprocessing.clean_data import clean_market_data

log = logging.getLogger(__name__)


def compute_quant_metrics(
    ticker: str,
    period: str = "2y",
    benchmark_ticker: str = "^GSPC",
    risk_free_rate_ann: float = 0.045,
) -> Dict[str, Any]:
    """Compute comprehensive quantitative analytics for a stock against a benchmark.
    
    Args:
        ticker: Asset ticker symbol (e.g., NVDA, AAPL, RELIANCE.NS)
        period: Historical lookback period (e.g., '1y', '2y', '5y')
        benchmark_ticker: Benchmark index ticker (default: ^GSPC for S&P 500, ^NSEI for Nifty)
        risk_free_rate_ann: Annualized risk-free benchmark rate (default: 4.5%)
        
    Returns:
        Structured dictionary containing price series, technical indicators,
        rolling volatility, beta, alpha, drawdowns, and momentum metrics.
    """
    clean_ticker = validate_ticker(ticker)
    clean_benchmark = validate_ticker(benchmark_ticker)

    # 1. Fetch historical OHLCV data
    df_raw = fetch_market_data(clean_ticker, period=period)
    df = clean_market_data(df_raw) if df_raw is not None and not df_raw.empty else pd.DataFrame()
    if df.empty or len(df) < 20:
        raise ValueError(f"Insufficient historical data for {clean_ticker} (found {len(df)} bars).")

    close = df["Close"].astype(float)
    high = df["High"].astype(float)
    low = df["Low"].astype(float)
    volume = df["Volume"].astype(float)

    # 2. Daily returns & Cumulative growth
    daily_returns = close.pct_change().dropna()
    cumulative_returns = (1.0 + daily_returns).cumprod() - 1.0

    # 3. Moving Averages
    sma_20 = close.rolling(20).mean()
    sma_50 = close.rolling(50).mean()
    sma_200 = close.rolling(min(200, len(close))).mean()
    ema_20 = close.ewm(span=20, adjust=False).mean()

    # 4. Volatility (Annualized using 252 trading sessions)
    rolling_vol_20d = daily_returns.rolling(20).std() * np.sqrt(252)
    rolling_vol_60d = daily_returns.rolling(min(60, len(daily_returns))).std() * np.sqrt(252)
    hist_vol_ann = float(daily_returns.std() * np.sqrt(252))

    # 5. RSI (14-day Relative Strength Index)
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / 14, min_periods=14, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / 14, min_periods=14, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi_14 = 100 - (100 / (1 + rs))

    # 6. Momentum Indicators (% price return over windows)
    def _pct_change_n(n: int) -> float:
        if len(close) > n and close.iloc[-n - 1] > 0:
            return float((close.iloc[-1] / close.iloc[-n - 1] - 1.0) * 100)
        return float((close.iloc[-1] / close.iloc[0] - 1.0) * 100)

    momentum_1m = _pct_change_n(21)
    momentum_3m = _pct_change_n(63)
    momentum_6m = _pct_change_n(126)
    momentum_12m = _pct_change_n(252)

    # 7. Drawdown Series & Maximum Drawdown
    running_max = close.cummax()
    drawdown_series = (close - running_max) / running_max
    max_drawdown_pct = float(drawdown_series.min() * 100)

    # Calculate drawdown peak, trough, and recovery duration
    trough_idx = drawdown_series.idxmin()
    peak_idx = close.loc[:trough_idx].idxmax() if trough_idx is not None else None
    
    # 8. Benchmark Comparison & Regression Metrics (Beta, Alpha, R²)
    df_bm_raw = fetch_market_data(clean_benchmark, period=period)
    df_bm = clean_market_data(df_bm_raw) if df_bm_raw is not None and not df_bm_raw.empty else pd.DataFrame()

    beta = 1.0
    alpha_ann = 0.0
    r_squared = 0.0
    correlation = 0.0
    up_capture = 100.0
    down_capture = 100.0
    bm_returns = pd.Series(dtype=float)
    rel_strength = pd.Series(dtype=float)

    if not df_bm.empty and len(df_bm) >= 20:
        bm_close = df_bm["Close"].astype(float)
        bm_returns = bm_close.pct_change().dropna()

        # Align on dates
        aligned = pd.concat([daily_returns, bm_returns], axis=1, keys=["asset", "benchmark"]).dropna()
        if len(aligned) >= 15:
            r_asset = aligned["asset"]
            r_bench = aligned["benchmark"]

            # Linear regression: asset_return = alpha + beta * bench_return
            slope, intercept, r_value, p_value, std_err = stats.linregress(r_bench, r_asset)
            beta = float(slope)
            r_squared = float(r_value ** 2)
            correlation = float(r_value)
            
            # Annualized Jensen's Alpha: excess return above CAPM expectation
            mean_rf_daily = risk_free_rate_ann / 252
            expected_excess = mean_rf_daily + beta * (r_bench.mean() - mean_rf_daily)
            alpha_ann = float((r_asset.mean() - expected_excess) * 252 * 100)

            # Up and Down capture ratios
            up_market = aligned[aligned["benchmark"] > 0]
            if len(up_market) > 0 and up_market["benchmark"].mean() != 0:
                up_capture = float((up_market["asset"].mean() / up_market["benchmark"].mean()) * 100)

            down_market = aligned[aligned["benchmark"] < 0]
            if len(down_market) > 0 and down_market["benchmark"].mean() != 0:
                down_capture = float((down_market["asset"].mean() / down_market["benchmark"].mean()) * 100)

            # Relative Strength series (asset growth / benchmark growth)
            cum_asset = (1.0 + r_asset).cumprod()
            cum_bench = (1.0 + r_bench).cumprod()
            rel_strength = cum_asset / cum_bench

    # 9. Risk-Adjusted Ratios
    total_return_pct = float(cumulative_returns.iloc[-1] * 100) if len(cumulative_returns) > 0 else 0.0
    years = max(len(daily_returns) / 252.0, 0.1)
    cagr_pct = float(((1.0 + total_return_pct / 100.0) ** (1.0 / years) - 1.0) * 100)
    
    calmar_ratio = float(abs(cagr_pct / max_drawdown_pct)) if max_drawdown_pct < 0 else 0.0

    excess_returns = daily_returns - (risk_free_rate_ann / 252)
    sharpe_ratio = float((excess_returns.mean() / daily_returns.std() * np.sqrt(252))) if daily_returns.std() > 0 else 0.0

    downside_returns = daily_returns[daily_returns < 0]
    downside_std = downside_returns.std() * np.sqrt(252)
    sortino_ratio = float((excess_returns.mean() * 252 / downside_std)) if downside_std > 0 else 0.0

    return {
        "ticker": clean_ticker,
        "benchmark_ticker": clean_benchmark,
        "period": period,
        "data_points": len(df),
        "start_date": str(df.index[0].date()) if hasattr(df.index[0], "date") else str(df.index[0]),
        "end_date": str(df.index[-1].date()) if hasattr(df.index[-1], "date") else str(df.index[-1]),
        "latest_price": float(close.iloc[-1]),
        "total_return_pct": round(total_return_pct, 2),
        "cagr_pct": round(cagr_pct, 2),
        "historical_volatility_ann": round(hist_vol_ann * 100, 2),
        "max_drawdown_pct": round(max_drawdown_pct, 2),
        "calmar_ratio": round(calmar_ratio, 2),
        "sharpe_ratio": round(sharpe_ratio, 2),
        "sortino_ratio": round(sortino_ratio, 2),
        "beta": round(beta, 2),
        "alpha_ann_pct": round(alpha_ann, 2),
        "r_squared": round(r_squared, 3),
        "correlation_with_benchmark": round(correlation, 3),
        "up_capture_ratio": round(up_capture, 1),
        "down_capture_ratio": round(down_capture, 1),
        "momentum": {
            "1m_pct": round(momentum_1m, 2),
            "3m_pct": round(momentum_3m, 2),
            "6m_pct": round(momentum_6m, 2),
            "12m_pct": round(momentum_12m, 2),
        },
        "latest_rsi14": round(float(rsi_14.dropna().iloc[-1]), 1) if not rsi_14.dropna().empty else 50.0,
        "series": {
            "dates": [str(d.date()) if hasattr(d, "date") else str(d) for d in df.index],
            "close": close.tolist(),
            "open": df["Open"].astype(float).tolist(),
            "high": high.tolist(),
            "low": low.tolist(),
            "volume": volume.tolist(),
            "daily_returns": daily_returns.tolist(),
            "cumulative_returns": cumulative_returns.tolist(),
            "sma_20": [None if np.isnan(v) else round(v, 2) for v in sma_20],
            "sma_50": [None if np.isnan(v) else round(v, 2) for v in sma_50],
            "sma_200": [None if np.isnan(v) else round(v, 2) for v in sma_200],
            "ema_20": [None if np.isnan(v) else round(v, 2) for v in ema_20],
            "rsi_14": [None if np.isnan(v) else round(v, 1) for v in rsi_14],
            "rolling_vol_20d": [None if np.isnan(v) else round(v * 100, 2) for v in rolling_vol_20d],
            "rolling_vol_60d": [None if np.isnan(v) else round(v * 100, 2) for v in rolling_vol_60d],
            "drawdown": [None if np.isnan(v) else round(v * 100, 2) for v in drawdown_series],
            "relative_strength": [None if np.isnan(v) else round(v, 3) for v in rel_strength] if not rel_strength.empty else [],
        },
        "trough_date": str(trough_idx.date()) if hasattr(trough_idx, "date") else str(trough_idx),
        "peak_date": str(peak_idx.date()) if hasattr(peak_idx, "date") else str(peak_idx),
    }


def compare_peer_assets(tickers: List[str], period: str = "1y") -> Dict[str, Any]:
    """Calculate comparative return, volatility, and correlation across multiple peer assets."""
    results = {}
    return_series = {}

    for t in tickers:
        try:
            m = compute_quant_metrics(t, period=period)
            results[t] = {
                "latest_price": m["latest_price"],
                "total_return_pct": m["total_return_pct"],
                "volatility_ann_pct": m["historical_volatility_ann"],
                "sharpe_ratio": m["sharpe_ratio"],
                "max_drawdown_pct": m["max_drawdown_pct"],
                "beta": m["beta"],
            }
            return_series[t] = pd.Series(m["series"]["daily_returns"])
        except Exception as exc:
            log.warning("Peer analysis failed for %s: %s", t, exc)

    # Correlation matrix across peers
    corr_matrix = {}
    if len(return_series) >= 2:
        df_ret = pd.DataFrame(return_series).dropna()
        if not df_ret.empty:
            corr_df = df_ret.corr()
            corr_matrix = {col: corr_df[col].to_dict() for col in corr_df.columns}

    return {
        "period": period,
        "assets": results,
        "correlation_matrix": corr_matrix,
    }
