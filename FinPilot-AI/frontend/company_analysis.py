"""Company technical & global fundamental analysis page."""
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from backend.data.global_exchanges import format_currency_amount, CURRENCY_SYMBOLS


def render_company_analysis():
    """Render comprehensive technical indicators and global fundamental metrics."""
    analysis = st.session_state.get("analysis")
    if not analysis:
        st.info("💡 Please search or select a company on the **Dashboard** and click **Run Comprehensive Global Analysis** first.")
        return

    ticker = analysis["ticker"]
    fundamentals = analysis.get("fundamentals", {})
    market_df = analysis.get("market")
    features_df = analysis.get("features")
    
    comp_name = analysis.get("company_name", ticker)
    country = analysis.get("country", "Global")
    exchange = analysis.get("exchange", "Exchange")
    curr_code = analysis.get("currency", "USD")
    curr_sym = analysis.get("currency_symbol", CURRENCY_SYMBOLS.get(curr_code, curr_code))
    flag = analysis.get("flag", "🌐")

    st.markdown(f"## 📊 Quantitative Technical & Fundamental Analysis — {flag} {comp_name} ({ticker})")
    st.markdown(f"<p style='color: #94a3b8; margin-top: -8px;'>Exchange: <b>{exchange}</b> | Country: <b>{country}</b> | Reporting Currency: <b>{curr_code} ({curr_sym})</b></p>", unsafe_allow_html=True)

    if market_df is None or market_df.empty:
        st.warning("No market data available for this company.")
        return

    # -------------------------------------------------------------
    # Global Fundamental Statements & Financial Health Row
    # -------------------------------------------------------------
    st.markdown("### 🏛️ Financial Fundamentals & Reporting Statements")
    
    mcap = fundamentals.get("market_cap")
    rev = fundamentals.get("revenue")
    net_inc = fundamentals.get("net_income")
    cflow = fundamentals.get("operating_cash_flow")
    pe = fundamentals.get("pe_ratio")
    eps = fundamentals.get("eps")
    pm = fundamentals.get("profit_margin")
    rg = fundamentals.get("revenue_growth")
    de = fundamentals.get("debt_to_equity")

    def _fmt_large(val):
        if val is None:
            return "N/A"
        abs_v = abs(val)
        if abs_v >= 1e12:
            return f"{curr_sym}{val/1e12:.2f}T {curr_code}"
        if abs_v >= 1e9:
            return f"{curr_sym}{val/1e9:.2f}B {curr_code}"
        if abs_v >= 1e6:
            return f"{curr_sym}{val/1e6:.2f}M {curr_code}"
        return f"{curr_sym}{val:,.2f} {curr_code}"

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.metric("Market Capitalization", _fmt_large(mcap))
    with c2:
        st.metric(f"Total Revenue ({curr_code})", _fmt_large(rev))
    with c3:
        st.metric(f"Net Income ({curr_code})", _fmt_large(net_inc))
    with c4:
        st.metric("Operating Cash Flow", _fmt_large(cflow))
    with c5:
        st.metric("Trailing P/E Ratio", f"{pe:.2f}" if pe else "N/A")

    # Second row of financial statement fundamentals
    c6, c7, c8, c9, c10 = st.columns(5)
    with c6:
        st.metric(f"EPS ({curr_code})", f"{curr_sym}{eps:.2f}" if eps else "N/A")
    with c7:
        st.metric("Profit Margin", f"{pm*100:.1f}%" if pm else "N/A")
    with c8:
        st.metric("Revenue Growth", f"{rg*100:.1f}%" if rg else "N/A")
    with c9:
        st.metric("Debt-to-Equity", f"{de:.2f}" if de else "N/A")
    with c10:
        beta = fundamentals.get("beta")
        st.metric("Market Beta", f"{beta:.2f}" if beta else "N/A")

    st.caption(
        f"ℹ️ **Reporting Currency Notice:** All accounting figures are reported in **{curr_code} ({curr_sym})** directly from official provider financial statements. "
        "Missing fields remain unpopulated to prevent fabricated financial records."
    )

    # -------------------------------------------------------------
    # Interactive Multi-Panel Technical Chart
    # -------------------------------------------------------------
    st.markdown("### 📈 Interactive Multi-Panel Technical Chart")
    with st.expander("🛠️ Chart Indicator Overlays", expanded=False):
        ch1, ch2, ch3, ch4 = st.columns(4)
        show_sma20 = ch1.checkbox("SMA 20 (Yellow)", value=True)
        show_sma50 = ch2.checkbox("SMA 50 (Purple)", value=True)
        show_ema20 = ch3.checkbox("EMA 20 (Cyan)", value=False)
        show_bb = ch4.checkbox("Bollinger Bands (20, 2σ)", value=True)

    fig = make_subplots(
        rows=4,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.55, 0.15, 0.15, 0.15],
        subplot_titles=(
            f"{ticker} OHLCV Candlestick & Technical Bands ({curr_code})",
            "Exchange Trading Session Volume",
            "Relative Strength Index (RSI 14)",
            "MACD (12, 26, 9 Momentum)",
        ),
    )

    # 1. Candlestick
    fig.add_trace(
        go.Candlestick(
            x=market_df.index,
            open=market_df["Open"],
            high=market_df["High"],
            low=market_df["Low"],
            close=market_df["Close"],
            name="OHLC",
            increasing_line_color="#10b981",
            decreasing_line_color="#f43f5e",
        ),
        row=1, col=1,
    )

    # Moving Average Overlays
    if show_sma20 and "SMA20" in features_df.columns:
        fig.add_trace(
            go.Scatter(x=features_df.index, y=features_df["SMA20"], name="SMA 20", line=dict(color="#f59e0b", width=1.5)),
            row=1, col=1,
        )
    if show_sma50 and "SMA50" in features_df.columns:
        fig.add_trace(
            go.Scatter(x=features_df.index, y=features_df["SMA50"], name="SMA 50", line=dict(color="#a855f7", width=1.5)),
            row=1, col=1,
        )
    if show_ema20 and "EMA20" in features_df.columns:
        fig.add_trace(
            go.Scatter(x=features_df.index, y=features_df["EMA20"], name="EMA 20", line=dict(color="#38bdf8", width=1.5)),
            row=1, col=1,
        )
    if show_bb and "BB_Upper" in features_df.columns and "BB_Lower" in features_df.columns:
        fig.add_trace(
            go.Scatter(x=features_df.index, y=features_df["BB_Upper"], name="Upper BB", line=dict(color="rgba(148, 163, 184, 0.4)", dash="dot")),
            row=1, col=1,
        )
        fig.add_trace(
            go.Scatter(x=features_df.index, y=features_df["BB_Lower"], name="Lower BB", line=dict(color="rgba(148, 163, 184, 0.4)", dash="dot")),
            row=1, col=1,
        )

    # 2. Volume
    colors = ["#10b981" if c >= o else "#f43f5e" for c, o in zip(market_df["Close"], market_df["Open"])]
    fig.add_trace(
        go.Bar(x=market_df.index, y=market_df["Volume"], name="Volume", marker_color=colors, opacity=0.8),
        row=2, col=1,
    )

    # 3. RSI
    if "rsi14" in features_df.columns:
        fig.add_trace(
            go.Scatter(x=features_df.index, y=features_df["rsi14"], name="RSI (14)", line=dict(color="#ec4899", width=1.5)),
            row=3, col=1,
        )
        fig.add_hline(y=70, line_dash="dash", line_color="#f43f5e", line_width=1, row=3, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="#10b981", line_width=1, row=3, col=1)

    # 4. MACD
    if "macd" in features_df.columns and "macd_signal" in features_df.columns:
        fig.add_trace(
            go.Scatter(x=features_df.index, y=features_df["macd"], name="MACD", line=dict(color="#38bdf8", width=1.5)),
            row=4, col=1,
        )
        fig.add_trace(
            go.Scatter(x=features_df.index, y=features_df["macd_signal"], name="Signal", line=dict(color="#f97316", width=1.5)),
            row=4, col=1,
        )
        if "macd_histogram" in features_df.columns:
            hist_colors = ["#10b981" if h >= 0 else "#f43f5e" for h in features_df["macd_histogram"]]
            fig.add_trace(
                go.Bar(x=features_df.index, y=features_df["macd_histogram"], name="Histogram", marker_color=hist_colors),
                row=4, col=1,
            )

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=850,
        margin=dict(l=0, r=0, t=30, b=0),
        xaxis_rangeslider_visible=False,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        yaxis=dict(tickprefix=curr_sym, title=f"Price ({curr_code})"),
    )

    st.plotly_chart(fig, use_container_width=True)

    # -------------------------------------------------------------
    # Corporate Profile & Historical Price Records
    # -------------------------------------------------------------
    tab_profile, tab_table = st.tabs(["Global Company Profile & Description", f"Historical OHLCV Records ({curr_code})"])
    with tab_profile:
        st.write(fundamentals.get("description", "No company profile description available."))
        if fundamentals.get("website"):
            st.markdown(f"**Official Corporate Website:** [{fundamentals.get('website')}]({fundamentals.get('website')})")

    with tab_table:
        st.dataframe(
            market_df.sort_index(ascending=False).head(100),
            use_container_width=True,
        )
