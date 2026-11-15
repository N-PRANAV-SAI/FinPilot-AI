"""FinPilot AI — Quantitative Research Lab Page.

Institutional workspace for time series analysis, moving averages, rolling volatility,
RSI momentum, beta regression, running drawdowns, and benchmark relative strength.
"""
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np

from backend.analytics.quant_research import compute_quant_metrics
from backend.data.global_exchanges import format_currency_amount

BENCHMARK_CHOICES = {
    "S&P 500 (^GSPC)": "^GSPC",
    "NIFTY 50 (^NSEI)": "^NSEI",
    "NASDAQ Composite (^IXIC)": "^IXIC",
    "DAX Performance (^GDAXI)": "^GDAXI",
}


def render_quant_research_lab():
    """Render institutional quantitative research workspace."""
    st.markdown("""
        <div style="margin-bottom: 20px;">
            <div style="display: flex; align-items: center; gap: 10px;">
                <span style="font-size: 2rem;">🔬</span>
                <div>
                    <h1 style="margin: 0; font-size: 1.85rem; font-weight: 800; color: #f8fafc;">
                        Quantitative Research Lab
                    </h1>
                    <span style="color: #64748b; font-size: 0.85rem; font-weight: 600;">
                        Institutional Empirical Analysis • Rolling Volatility • Beta & Market Regressions
                    </span>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Asset and Benchmark Configuration Bar
    c1, c2, c3 = st.columns([2, 1, 2])
    with c1:
        ticker = st.text_input("Target Asset Ticker", value="NVDA", help="Supports 22+ global exchanges (e.g., NVDA, RELIANCE.NS, AAPL, 7203.T)").strip().upper()
    with c2:
        period = st.selectbox("Historical Lookback", ["1y", "2y", "3y", "5y"], index=1)
    with c3:
        bm_label = st.selectbox("Benchmark Index", list(BENCHMARK_CHOICES.keys()), index=0)
        benchmark_ticker = BENCHMARK_CHOICES[bm_label]

    try:
        with st.spinner(f"Computing quantitative empirical metrics for {ticker}..."):
            m = compute_quant_metrics(ticker, period=period, benchmark_ticker=benchmark_ticker)
    except Exception as e:
        st.error(f"Could not compute quantitative analytics for {ticker}: {e}")
        return

    # Top Executive Quantitative KPI Row
    kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
    with kpi1:
        st.metric("Total Return", f"{m['total_return_pct']:+.2f}%", delta=f"{m['cagr_pct']:+.1f}% CAGR")
    with kpi2:
        st.metric("Annual Volatility", f"{m['historical_volatility_ann']:.1f}%", help="Annualized daily standard deviation (252 sessions)")
    with kpi3:
        st.metric("Beta vs Benchmark", f"{m['beta']:.2f}", help=f"Sensitivity vs {m['benchmark_ticker']}")
    with kpi4:
        st.metric("Max Drawdown", f"{m['max_drawdown_pct']:.1f}%", help="Peak-to-trough historical drop")
    with kpi5:
        st.metric("Sharpe Ratio", f"{m['sharpe_ratio']:.2f}", delta=f"Sortino: {m['sortino_ratio']:.2f}")

    # Section 1: Candlesticks with Moving Average Envelopes
    st.markdown("### 📈 Price Series & Moving Average Envelopes")
    dates = m["series"]["dates"]
    closes = m["series"]["close"]

    fig_price = go.Figure()
    fig_price.add_trace(go.Scatter(x=dates, y=closes, name="Close Price", line=dict(color="#38bdf8", width=2)))
    if m["series"]["sma_20"]:
        fig_price.add_trace(go.Scatter(x=dates, y=m["series"]["sma_20"], name="SMA 20", line=dict(color="#10b981", width=1.2, dash="dash")))
    if m["series"]["sma_50"]:
        fig_price.add_trace(go.Scatter(x=dates, y=m["series"]["sma_50"], name="SMA 50", line=dict(color="#f59e0b", width=1.2, dash="dash")))
    if m["series"]["sma_200"]:
        fig_price.add_trace(go.Scatter(x=dates, y=m["series"]["sma_200"], name="SMA 200", line=dict(color="#ef4444", width=1.5)))

    fig_price.update_layout(
        template="plotly_dark",
        plot_bgcolor="#0f172a",
        paper_bgcolor="#0f172a",
        margin=dict(l=0, r=0, t=10, b=0),
        height=380,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis=dict(showgrid=True, gridcolor="#1e293b"),
        yaxis=dict(showgrid=True, gridcolor="#1e293b"),
    )
    st.plotly_chart(fig_price, use_container_width=True)

    # Section 2: Rolling Volatility and Running Drawdowns
    col_v, col_d = st.columns(2)
    with col_v:
        st.markdown("### ⚡ Rolling Volatility (20d vs 60d)")
        fig_vol = go.Figure()
        fig_vol.add_trace(go.Scatter(x=dates, y=m["series"]["rolling_vol_20d"], name="20-Day Rolling Vol", line=dict(color="#38bdf8", width=1.5)))
        fig_vol.add_trace(go.Scatter(x=dates, y=m["series"]["rolling_vol_60d"], name="60-Day Rolling Vol", line=dict(color="#a855f7", width=1.5)))
        fig_vol.update_layout(
            template="plotly_dark",
            plot_bgcolor="#0f172a",
            paper_bgcolor="#0f172a",
            margin=dict(l=0, r=0, t=10, b=0),
            height=280,
            yaxis=dict(ticksuffix="%", gridcolor="#1e293b"),
            xaxis=dict(gridcolor="#1e293b"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        st.plotly_chart(fig_vol, use_container_width=True)

    with col_d:
        st.markdown("### 🔻 Running Drawdown from Peak")
        fig_dd = go.Figure()
        fig_dd.add_trace(go.Scatter(x=dates, y=m["series"]["drawdown"], name="Drawdown", fill="tozeroy", fillcolor="rgba(239, 68, 68, 0.2)", line=dict(color="#ef4444", width=1.5)))
        fig_dd.update_layout(
            template="plotly_dark",
            plot_bgcolor="#0f172a",
            paper_bgcolor="#0f172a",
            margin=dict(l=0, r=0, t=10, b=0),
            height=280,
            yaxis=dict(ticksuffix="%", gridcolor="#1e293b"),
            xaxis=dict(gridcolor="#1e293b"),
        )
        st.plotly_chart(fig_dd, use_container_width=True)

    # Section 3: Momentum Indicators & Relative Strength
    st.markdown("### 🚀 Multi-Timeframe Momentum Profile")
    m_cols = st.columns(4)
    mom_data = [
        ("1 Month (21d)", m["momentum"]["1m_pct"]),
        ("3 Months (63d)", m["momentum"]["3m_pct"]),
        ("6 Months (126d)", m["momentum"]["6m_pct"]),
        ("12 Months (252d)", m["momentum"]["12m_pct"]),
    ]
    for idx, (label, val) in enumerate(mom_data):
        with m_cols[idx]:
            color = "#10b981" if val >= 0 else "#ef4444"
            st.markdown(f"""
                <div style="background: #1e293b; border-radius: 12px; padding: 14px; border: 1px solid #334155; text-align: center;">
                    <div style="font-size: 0.75rem; color: #94a3b8; font-weight: 700; text-transform: uppercase;">{label}</div>
                    <div style="font-size: 1.4rem; font-weight: 800; color: {color}; margin-top: 4px;">{val:+.2f}%</div>
                </div>
            """, unsafe_allow_html=True)

    # Section 4: Quantitative Audit Table
    st.markdown("### 📋 Empirical Performance & Factor Attribution")
    stat_df = pd.DataFrame([
        {"Metric": "Asset Ticker", "Value": m["ticker"]},
        {"Metric": "Benchmark Ticker", "Value": m["benchmark_ticker"]},
        {"Metric": "Observation Window", "Value": f"{m['start_date']} to {m['end_date']} ({m['data_points']} sessions)"},
        {"Metric": "CAGR (Annualized)", "Value": f"{m['cagr_pct']:+.2f}%"},
        {"Metric": "Annualized Volatility", "Value": f"{m['historical_volatility_ann']:.2f}%"},
        {"Metric": "Beta vs Benchmark", "Value": f"{m['beta']:.2f}"},
        {"Metric": "Jensen's Alpha (Annualized)", "Value": f"{m['alpha_ann_pct']:+.2f}%"},
        {"Metric": "R-Squared (Explained Variance)", "Value": f"{m['r_squared']:.3f}"},
        {"Metric": "Correlation vs Benchmark", "Value": f"{m['correlation_with_benchmark']:.3f}"},
        {"Metric": "Up-Market Capture Ratio", "Value": f"{m['up_capture_ratio']:.1f}%"},
        {"Metric": "Down-Market Capture Ratio", "Value": f"{m['down_capture_ratio']:.1f}%"},
        {"Metric": "Calmar Ratio (CAGR / MDD)", "Value": f"{m['calmar_ratio']:.2f}"},
        {"Metric": "Deepest Drawdown Trough Date", "Value": m["trough_date"]},
    ])
    st.dataframe(stat_df, use_container_width=True, hide_index=True)

    st.caption("⚠️ **Empirical Disclosure**: All metrics represent strictly historical mathematical calculations. Past volatility and correlations do not guarantee future performance.")
