"""FinPilot AI — Historical Strategy Backtesting Engine.

Implements realistic strategy backtesting with strict look-ahead bias prevention:
- All indicator calculations use strictly past/closed bar data.
- Trading signals calculated at the Close of bar t are executed at the Open of bar t+1.
- Realistic transaction fees (default: 0.10%) and market slippage (default: 0.05%) deducted on every order.
- Equity curve, drawdowns, Sharpe, Sortino, win rates, and benchmark comparisons computed rigorously.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd

from backend.data.market_data import fetch_market_data, validate_ticker
from backend.preprocessing.clean_data import clean_market_data

log = logging.getLogger(__name__)


def run_backtest(
    ticker: str,
    strategy_name: str = "Moving Average Crossover",
    strategy_params: Optional[Dict[str, Any]] = None,
    period: str = "2y",
    initial_capital: float = 100000.0,
    transaction_cost_pct: float = 0.001,  # 0.10% commission
    slippage_pct: float = 0.0005,         # 0.05% slippage
    benchmark_ticker: str = "^GSPC",
    risk_free_rate_ann: float = 0.045,
) -> Dict[str, Any]:
    """Execute historical strategy backtest with strict anti-leakage execution logic."""
    clean_ticker = validate_ticker(ticker)
    clean_benchmark = validate_ticker(benchmark_ticker)
    params = strategy_params or {}

    # 1. Fetch and clean OHLCV data
    df_raw = fetch_market_data(clean_ticker, period=period)
    df = clean_market_data(df_raw) if df_raw is not None and not df_raw.empty else pd.DataFrame()
    if df.empty or len(df) < 50:
        raise ValueError(f"Insufficient historical data for backtesting {clean_ticker} (found {len(df)} bars).")

    opens = df["Open"].astype(float)
    closes = df["Close"].astype(float)
    highs = df["High"].astype(float)
    lows = df["Low"].astype(float)
    volumes = df["Volume"].astype(float)
    n = len(df)

    # 2. Generate Strategy Signals (1 = Long, 0 = Flat/Cash)
    signals = pd.Series(0, index=df.index, dtype=int)
    strat_key = strategy_name.lower()

    if "buy" in strat_key and "hold" in strat_key:
        # Buy & Hold: Always long from bar 1
        signals[:] = 1

    elif "moving average" in strat_key or "crossover" in strat_key:
        fast_window = int(params.get("fast_period", 20))
        slow_window = int(params.get("slow_period", 50))
        fast_sma = closes.rolling(fast_window).mean()
        slow_sma = closes.rolling(slow_window).mean()
        signals[fast_sma > slow_sma] = 1

    elif "rsi" in strat_key:
        rsi_period = int(params.get("rsi_period", 14))
        oversold = float(params.get("oversold", 30.0))
        overbought = float(params.get("overbought", 70.0))

        delta = closes.diff()
        gain = delta.clip(lower=0).ewm(alpha=1 / rsi_period, min_periods=rsi_period, adjust=False).mean()
        loss = (-delta.clip(upper=0)).ewm(alpha=1 / rsi_period, min_periods=rsi_period, adjust=False).mean()
        rs = gain / loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))

        # Position holds long after oversold until overbought
        pos = 0
        sig_list = []
        for val in rsi:
            if np.isnan(val):
                sig_list.append(0)
            elif val < oversold:
                pos = 1
                sig_list.append(1)
            elif val > overbought:
                pos = 0
                sig_list.append(0)
            else:
                sig_list.append(pos)
        signals = pd.Series(sig_list, index=df.index)

    elif "momentum" in strat_key:
        lookback = int(params.get("momentum_lookback", 20))
        threshold = float(params.get("momentum_threshold_pct", 2.0)) / 100.0
        mom = closes / closes.shift(lookback) - 1.0
        signals[mom > threshold] = 1

    elif "mean reversion" in strat_key:
        std_window = int(params.get("bb_window", 20))
        num_std = float(params.get("num_std", 2.0))
        mid = closes.rolling(std_window).mean()
        std = closes.rolling(std_window).std()
        lower = mid - num_std * std

        # Buy when price dips below lower band, exit when it crosses above mid
        pos = 0
        sig_list = []
        for c, l_band, m_band in zip(closes, lower, mid):
            if np.isnan(l_band):
                sig_list.append(0)
            elif c <= l_band:
                pos = 1
                sig_list.append(1)
            elif c >= m_band:
                pos = 0
                sig_list.append(0)
            else:
                sig_list.append(pos)
        signals = pd.Series(sig_list, index=df.index)

    else:
        # Default: SMA 20/50 Crossover
        fast_sma = closes.rolling(20).mean()
        slow_sma = closes.rolling(50).mean()
        signals[fast_sma > slow_sma] = 1

    # 3. Simulate Trade Executions: Signal at Close(t) -> Execute at Open(t+1)
    cash = initial_capital
    shares = 0.0
    equity_curve = []
    trade_log = []
    total_friction = 0.0
    trade_returns = []
    current_entry_price = 0.0

    for i in range(n):
        date_str = str(df.index[i].date()) if hasattr(df.index[i], "date") else str(df.index[i])
        current_open = float(opens.iloc[i])
        current_close = float(closes.iloc[i])

        # Execution check: Look at signal generated on previous bar (i-1)
        if i > 0:
            desired_pos = signals.iloc[i - 1]
            current_pos = 1 if shares > 0 else 0

            # Signal BUY: Enter position
            if desired_pos == 1 and current_pos == 0:
                exec_price = current_open * (1.0 + slippage_pct)
                fee = cash * transaction_cost_pct
                investable = cash - fee
                if investable > 0 and exec_price > 0:
                    shares = investable / exec_price
                    total_friction += fee
                    current_entry_price = exec_price
                    cash = 0.0
                    trade_log.append({
                        "date": date_str,
                        "action": "BUY",
                        "price": round(exec_price, 2),
                        "shares": round(shares, 4),
                        "cost": round(fee, 2),
                        "portfolio_value": round(shares * exec_price, 2),
                    })

            # Signal SELL: Exit position
            elif desired_pos == 0 and current_pos == 1:
                exec_price = current_open * (1.0 - slippage_pct)
                gross_proceeds = shares * exec_price
                fee = gross_proceeds * transaction_cost_pct
                cash = gross_proceeds - fee
                total_friction += fee
                
                # Trade return calculation
                if current_entry_price > 0:
                    t_ret = (exec_price / current_entry_price - 1.0) * 100
                    trade_returns.append(t_ret)

                trade_log.append({
                    "date": date_str,
                    "action": "SELL",
                    "price": round(exec_price, 2),
                    "shares": round(shares, 4),
                    "cost": round(fee, 2),
                    "portfolio_value": round(cash, 2),
                })
                shares = 0.0
                current_entry_price = 0.0

        # Mark-to-market portfolio value at Close
        current_val = cash + (shares * current_close)
        equity_curve.append(current_val)

    equity_series = pd.Series(equity_curve, index=df.index)
    total_return_pct = float((equity_series.iloc[-1] / initial_capital - 1.0) * 100)
    
    # CAGR
    years = max(n / 252.0, 0.1)
    cagr_pct = float(((equity_series.iloc[-1] / initial_capital) ** (1.0 / years) - 1.0) * 100)

    # Max Drawdown
    running_max = equity_series.cummax()
    drawdown_series = (equity_series - running_max) / running_max
    max_drawdown_pct = float(drawdown_series.min() * 100)

    # Strategy Returns, Sharpe and Sortino
    strat_daily_returns = equity_series.pct_change().dropna()
    mean_excess = strat_daily_returns.mean() - (risk_free_rate_ann / 252)
    strat_vol = strat_daily_returns.std() * np.sqrt(252)

    sharpe_ratio = float(mean_excess / strat_daily_returns.std() * np.sqrt(252)) if strat_daily_returns.std() > 0 else 0.0

    downside = strat_daily_returns[strat_daily_returns < 0]
    sortino_ratio = float(mean_excess / downside.std() * np.sqrt(252)) if not downside.empty and downside.std() > 0 else 0.0

    # Win rate and trade metrics
    total_trades = len(trade_returns)
    win_trades = [r for r in trade_returns if r > 0]
    win_rate_pct = round((len(win_trades) / total_trades * 100), 1) if total_trades > 0 else 0.0
    avg_trade_ret_pct = round(float(np.mean(trade_returns)), 2) if trade_returns else 0.0

    # Benchmark Buy & Hold performance
    bm_total_ret = 0.0
    bm_cagr = 0.0
    try:
        df_bm = clean_market_data(fetch_market_data(clean_benchmark, period=period))
        if not df_bm.empty:
            bm_close = df_bm["Close"].astype(float)
            bm_total_ret = float((bm_close.iloc[-1] / bm_close.iloc[0] - 1.0) * 100)
            bm_years = max(len(bm_close) / 252.0, 0.1)
            bm_cagr = float(((bm_close.iloc[-1] / bm_close.iloc[0]) ** (1.0 / bm_years) - 1.0) * 100)
    except Exception:
        pass

    # Buy & Hold for target stock
    bh_total_ret = float((closes.iloc[-1] / closes.iloc[0] - 1.0) * 100)
    bh_cagr = float(((closes.iloc[-1] / closes.iloc[0]) ** (1.0 / years) - 1.0) * 100)

    return {
        "ticker": clean_ticker,
        "strategy_name": strategy_name,
        "benchmark_ticker": clean_benchmark,
        "period": period,
        "start_date": str(df.index[0].date()) if hasattr(df.index[0], "date") else str(df.index[0]),
        "end_date": str(df.index[-1].date()) if hasattr(df.index[-1], "date") else str(df.index[-1]),
        "initial_capital": initial_capital,
        "final_capital": round(float(equity_series.iloc[-1]), 2),
        "total_return_pct": round(total_return_pct, 2),
        "cagr_pct": round(cagr_pct, 2),
        "max_drawdown_pct": round(max_drawdown_pct, 2),
        "sharpe_ratio": round(sharpe_ratio, 2),
        "sortino_ratio": round(sortino_ratio, 2),
        "annualized_volatility_pct": round(float(strat_vol * 100), 2),
        "win_rate_pct": win_rate_pct,
        "total_trades": total_trades,
        "avg_trade_return_pct": avg_trade_ret_pct,
        "total_friction_fees": round(total_friction, 2),
        "benchmark_total_return_pct": round(bm_total_ret, 2),
        "benchmark_cagr_pct": round(bm_cagr, 2),
        "alpha_vs_benchmark_pct": round(cagr_pct - bm_cagr, 2),
        "buy_and_hold_return_pct": round(bh_total_ret, 2),
        "buy_and_hold_cagr_pct": round(bh_cagr, 2),
        "alpha_vs_buy_and_hold_pct": round(cagr_pct - bh_cagr, 2),
        "trade_log": trade_log[-50:],  # Return up to 50 latest trades
        "series": {
            "dates": [str(d.date()) if hasattr(d, "date") else str(d) for d in df.index],
            "equity": [round(v, 2) for v in equity_series],
            "drawdown_pct": [round(v * 100, 2) for v in drawdown_series],
            "signals": signals.tolist(),
        },
        "anti_leakage_safeguards": [
            "Signals evaluated strictly on Close(t); order executions occur at Open(t+1).",
            f"Commission fee of {transaction_cost_pct * 100:.2f}% deducted on every filled order.",
            f"Execution slippage of {slippage_pct * 100:.2f}% applied against entry and exit prices.",
            "Zero look-ahead forward indicator window leakage.",
        ],
    }
