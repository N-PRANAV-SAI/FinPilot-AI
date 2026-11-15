"""FinPilot AI — Historical Strategy Backtesting Lab.

Empirical strategy simulation with strict anti-leakage safeguards:
Executions execute at Open(t+1) using signals generated on Close(t).
Incorporates transaction costs, market slippage, and benchmark comparison.
"""
import streamlit as st
import plotly.graph_objects as go
import pandas as pd

from backend.analytics.backtesting import run_backtest

STRATEGY_CHOICES = [
    "Moving Average Crossover",
    "RSI Oversold/Overbought",
    "Momentum Breakout",
    "Mean Reversion (Bollinger Bands)",
    "Buy & Hold (Benchmark)",
]


def render_backtesting_lab():
    """Render historical backtesting suite."""
    st.markdown("""
        <div style="margin-bottom: 20px;">
            <div style="display: flex; align-items: center; gap: 10px;">
                <span style="font-size: 2rem;">📉</span>
                <div>
                    <h1 style="margin: 0; font-size: 1.85rem; font-weight: 800; color: #f8fafc;">
                        Historical Strategy Backtesting Lab
                    </h1>
                    <span style="color: #64748b; font-size: 0.85rem; font-weight: 600;">
                        Strict Look-Ahead Bias Prevention • Next-Bar Open Execution • Slippage & Commission Modeling
                    </span>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Strategy Parameters Sidebar / Expander
    with st.expander("⚙️ Backtest Strategy Configuration", expanded=True):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            ticker = st.text_input("Asset Ticker", value="NVDA").strip().upper()
            strategy = st.selectbox("Trading Strategy", STRATEGY_CHOICES, index=0)
        with col2:
            period = st.selectbox("Backtest Horizon", ["1y", "2y", "3y", "5y"], index=1)
            capital = st.number_input("Starting Capital (Virtual)", value=100000, step=10000)
        with col3:
            comm_pct = st.number_input("Commission Fee (%)", value=0.10, step=0.01) / 100.0
            slippage_pct = st.number_input("Execution Slippage (%)", value=0.05, step=0.01) / 100.0
        with col4:
            benchmark = st.selectbox("Benchmark Index", ["^GSPC (S&P 500)", "^NSEI (Nifty 50)", "^IXIC (NASDAQ)"], index=0).split()[0]
            rf_rate = st.number_input("Risk-Free Rate (% Ann)", value=4.5, step=0.5) / 100.0

        # Strategy-specific parameter overrides
        params = {}
        if strategy == "Moving Average Crossover":
            c_f, c_s = st.columns(2)
            with c_f:
                params["fast_period"] = st.slider("Fast SMA Window", 5, 50, 20)
            with c_s:
                params["slow_period"] = st.slider("Slow SMA Window", 20, 200, 50)
        elif strategy == "RSI Oversold/Overbought":
            c_os, c_ob = st.columns(2)
            with c_os:
                params["oversold"] = st.slider("RSI Buy Level (Oversold)", 10, 45, 30)
            with c_ob:
                params["overbought"] = st.slider("RSI Sell Level (Overbought)", 55, 90, 70)

    # Run Backtest
    try:
        with st.spinner(f"Running historical backtest for {ticker} ({strategy})..."):
            res = run_backtest(
                ticker=ticker,
                strategy_name=strategy,
                strategy_params=params,
                period=period,
                initial_capital=float(capital),
                transaction_cost_pct=comm_pct,
                slippage_pct=slippage_pct,
                benchmark_ticker=benchmark,
                risk_free_rate_ann=rf_rate,
            )
    except Exception as e:
        st.error(f"Backtesting error: {e}")
        return

    # Top KPI Metrics Row
    k1, k2, k3, k4, k5, k6 = st.columns(6)
    with k1:
        st.metric("Total Return", f"{res['total_return_pct']:+.1f}%", delta=f"{res['cagr_pct']:+.1f}% CAGR")
    with k2:
        st.metric("Alpha vs Benchmark", f"{res['alpha_vs_benchmark_pct']:+.1f}%", help=f"CAGR excess return over {res['benchmark_ticker']}")
    with k3:
        st.metric("Max Drawdown", f"{res['max_drawdown_pct']:.1f}%", delta_color="inverse")
    with k4:
        st.metric("Sharpe Ratio", f"{res['sharpe_ratio']:.2f}", delta=f"Sortino: {res['sortino_ratio']:.2f}")
    with k5:
        st.metric("Win Rate", f"{res['win_rate_pct']:.1f}%", delta=f"{res['total_trades']} Trades")
    with k6:
        st.metric("Friction Paid", f"₹{res['total_friction_fees']:,.0f}", help="Total commission and slippage deducted")

    # Section 1: Equity Curve Comparison
    st.markdown("### 📈 Cumulative Equity Curve (Mark-to-Market)")
    dates = res["series"]["dates"]
    equity = res["series"]["equity"]

    fig_eq = go.Figure()
    fig_eq.add_trace(go.Scatter(x=dates, y=equity, name=f"Strategy: {strategy}", line=dict(color="#38bdf8", width=2.5)))

    fig_eq.update_layout(
        template="plotly_dark",
        plot_bgcolor="#0f172a",
        paper_bgcolor="#0f172a",
        margin=dict(l=0, r=0, t=10, b=0),
        height=360,
        yaxis=dict(title="Portfolio Value", gridcolor="#1e293b"),
        xaxis=dict(gridcolor="#1e293b"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    st.plotly_chart(fig_eq, use_container_width=True)

    # Section 2: Drawdown & Comparative Performance Table
    c_dd, c_tbl = st.columns([1, 1])
    with c_dd:
        st.markdown("### 🔻 Strategy Drawdown Profile")
        fig_dd = go.Figure()
        fig_dd.add_trace(go.Scatter(x=dates, y=res["series"]["drawdown_pct"], name="Drawdown", fill="tozeroy", fillcolor="rgba(239, 68, 68, 0.2)", line=dict(color="#ef4444", width=1.5)))
        fig_dd.update_layout(
            template="plotly_dark",
            plot_bgcolor="#0f172a",
            paper_bgcolor="#0f172a",
            margin=dict(l=0, r=0, t=10, b=0),
            height=260,
            yaxis=dict(ticksuffix="%", gridcolor="#1e293b"),
            xaxis=dict(gridcolor="#1e293b"),
        )
        st.plotly_chart(fig_dd, use_container_width=True)

    with c_tbl:
        st.markdown("### ⚖️ Strategy vs Benchmark Comparison")
        comp_df = pd.DataFrame([
            {"Metric": "Total Return", "Strategy": f"{res['total_return_pct']:+.1f}%", "Buy & Hold": f"{res['buy_and_hold_return_pct']:+.1f}%", "Benchmark Index": f"{res['benchmark_total_return_pct']:+.1f}%"},
            {"Metric": "CAGR", "Strategy": f"{res['cagr_pct']:+.1f}%", "Buy & Hold": f"{res['buy_and_hold_cagr_pct']:+.1f}%", "Benchmark Index": f"{res['benchmark_cagr_pct']:+.1f}%"},
            {"Metric": "Max Drawdown", "Strategy": f"{res['max_drawdown_pct']:.1f}%", "Buy & Hold": "Historical peak", "Benchmark Index": "N/A"},
            {"Metric": "Sharpe Ratio", "Strategy": f"{res['sharpe_ratio']:.2f}", "Buy & Hold": "Unadjusted", "Benchmark Index": "Market"},
            {"Metric": "Average Trade Return", "Strategy": f"{res['avg_trade_return_pct']:+.2f}%", "Buy & Hold": "Single Entry", "Benchmark Index": "N/A"},
        ])
        st.dataframe(comp_df, use_container_width=True, hide_index=True)

    # Section 3: Trade Execution Log
    st.markdown("### 📜 Simulated Trade Execution Log")
    trade_log = res.get("trade_log", [])
    if trade_log:
        st.dataframe(pd.DataFrame(trade_log), use_container_width=True, hide_index=True)
    else:
        st.info("No trading triggers were generated during this backtest window.")

    # Anti-leakage disclosure
    with st.expander("🛡️ Anti-Leakage & Realism Disclosures", expanded=False):
        for safeguard in res.get("anti_leakage_safeguards", []):
            st.markdown(f"- {safeguard}")
        st.caption("Past backtesting performance does not guarantee future market profitability. All results are simulated.")
