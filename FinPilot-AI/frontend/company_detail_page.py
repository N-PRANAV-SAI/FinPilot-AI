"""Professional Company Detail Page for FinPilot AI.
Inspired by Groww's simplicity and TradingView's analytical depth.
Integrates ML Predictions, FinBERT, SHAP, RAG, and Gemini LLM.
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from backend.data.market_data import fetch_market_data, get_latest_price
from backend.data.financial_data import fetch_fundamentals
from backend.data.news_data import fetch_news
from backend.data.filings_data import discover_company_documents
from backend.data.global_exchanges import get_exchange_info, format_currency_amount
from backend.services.analysis_service import run_full_analysis
from backend.trading.paper_engine import PaperTradingEngine, get_fx_rate
from database.db import get_session


def render_company_detail_page(ticker: str = None):
    """Render unified Groww + TradingView caliber company research & trading page."""
    user = st.session_state.get("user", {})
    user_id = user.get("user_id", 1)

    # Determine active ticker
    if not ticker:
        ticker = st.session_state.get("selected_ticker") or st.session_state.get("active_ticker") or "NVDA"

    # Fetch live quote & company metadata
    quote_info = get_latest_price(ticker)
    price = quote_info.get("price", 0.0) if quote_info else 0.0
    change = quote_info.get("change", 0.0) if quote_info else 0.0
    change_pct = quote_info.get("change_pct", 0.0) if quote_info else 0.0
    currency = quote_info.get("currency", "USD")

    # Fetch fundamentals
    fundamentals = fetch_fundamentals(ticker)
    comp_name = fundamentals.get("company_name", ticker)
    exchange = fundamentals.get("exchange", "US")
    country = fundamentals.get("country", "Global")
    curr_sym = fundamentals.get("currency_symbol", "$")
    market_cap = fundamentals.get("market_cap", "N/A")

    # Change color
    change_color = "#10b981" if change >= 0 else "#f43f5e"

    # -------------------------------------------------------------
    # 1. HEADER SECTION (Groww-style clean company card)
    # -------------------------------------------------------------
    st.markdown(f"""
        <div style="background: #0f172a; border: 1px solid #1e293b; border-radius: 14px; padding: 22px 26px; margin-bottom: 1.5rem;">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 16px;">
                <div>
                    <div style="display: flex; align-items: center; gap: 10px;">
                        <span style="font-size: 1.8rem;">🏢</span>
                        <h1 style="margin: 0; font-size: 1.85rem; font-weight: 800; color: #f8fafc;">
                            {comp_name}
                        </h1>
                        <span style="background: #1e293b; color: #38bdf8; font-weight: 700; padding: 4px 10px; border-radius: 6px; font-size: 0.9rem;">
                            {ticker}
                        </span>
                    </div>
                    <div style="color: #94a3b8; font-size: 0.88rem; margin-top: 6px;">
                        Exchange: <b>{exchange}</b> &nbsp;|&nbsp; 
                        Country: <b>{country}</b> &nbsp;|&nbsp; 
                        Sector: <b>{fundamentals.get('sector', 'N/A')}</b> &nbsp;|&nbsp; 
                        Market Cap: <b>{format_currency_amount(market_cap, currency, curr_sym) if isinstance(market_cap, (int, float)) else market_cap}</b>
                    </div>
                </div>
                <div style="text-align: right;">
                    <div style="font-size: 2.2rem; font-weight: 800; color: #f8fafc;">
                        {curr_sym}{price:,.2f} <span style="font-size: 1rem; color: #94a3b8; font-weight: 500;">{currency}</span>
                    </div>
                    <div style="color: {change_color}; font-size: 1.05rem; font-weight: 700;">
                        {change:+,.2f} ({change_pct:+.2f}%) Today
                    </div>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Fast Action Buttons: Buy, Sell, Ask AI, Add to Watchlist
    btn_c1, btn_c2, btn_c3, btn_c4 = st.columns([1.2, 1.2, 1.5, 1.2])
    with btn_c1:
        if st.button("🟢 Buy Virtually", use_container_width=True, type="primary"):
            st.session_state["active_ticker"] = ticker
            st.session_state["nav"] = "Orders"
            st.rerun()
    with btn_c2:
        if st.button("🔴 Sell Position", use_container_width=True):
            st.session_state["active_ticker"] = ticker
            st.session_state["nav"] = "Orders"
            st.rerun()
    with btn_c3:
        if st.button("🤖 Ask AI About This Stock", use_container_width=True):
            st.session_state["active_ticker"] = ticker
            st.session_state["nav"] = "AI Assistant"
            st.rerun()
    with btn_c4:
        if st.button("⭐ Add Watchlist", use_container_width=True):
            st.session_state["active_ticker"] = ticker
            st.session_state["nav"] = "Watchlist"
            st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # -------------------------------------------------------------
    # 2. INTERACTIVE TRADINGVIEW-STYLE CHART
    # -------------------------------------------------------------
    st.markdown("### 📈 Interactive Market Chart")
    
    # Time Horizon Selector
    timeframe_cols = st.columns([1, 1, 1, 1, 1, 1, 1, 5])
    timeframes = ["1M", "3M", "6M", "1Y", "5Y", "Max"]
    tf_selected = "1Y"
    for idx, tf in enumerate(timeframes):
        with timeframe_cols[idx]:
            if st.button(tf, key=f"tf_{tf}", use_container_width=True):
                st.session_state["chart_period"] = tf.lower()
                st.rerun()

    period = st.session_state.get("chart_period", "1y")

    # Fetch historical data
    with st.spinner(f"Loading {period.upper()} chart data for {ticker}..."):
        df = fetch_market_data(ticker, period=period)

    if df is not None and not df.empty:
        # Calculate Technical Overlays
        df["SMA20"] = df["Close"].rolling(20).mean()
        df["SMA50"] = df["Close"].rolling(50).mean()
        df["EMA20"] = df["Close"].ewm(span=20, adjust=False).mean()

        # Create multi-panel chart (Candlestick + Volume)
        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.04,
            row_heights=[0.75, 0.25],
            specs=[[{"secondary_y": False}], [{"secondary_y": False}]]
        )

        # Candlestick
        fig.add_trace(
            go.Candlestick(
                x=df.index,
                open=df["Open"],
                high=df["High"],
                low=df["Low"],
                close=df["Close"],
                name="OHLC",
                increasing_line_color="#10b981",
                decreasing_line_color="#f43f5e"
            ),
            row=1, col=1
        )

        # Moving Averages
        fig.add_trace(go.Scatter(x=df.index, y=df["SMA20"], name="SMA 20", line=dict(color="#f59e0b", width=1.2)), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df["SMA50"], name="SMA 50", line=dict(color="#38bdf8", width=1.2)), row=1, col=1)

        # Volume Bar Chart
        colors = ["#10b981" if c >= o else "#f43f5e" for c, o in zip(df["Close"], df["Open"])]
        fig.add_trace(
            go.Bar(x=df.index, y=df["Volume"], name="Volume", marker_color=colors, opacity=0.6),
            row=2, col=1
        )

        fig.update_layout(
            template="plotly_dark",
            height=460,
            margin=dict(l=10, r=10, t=10, b=10),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            xaxis_rangeslider_visible=False,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Historical price data currently unavailable for this asset.")

    st.markdown("<br>", unsafe_allow_html=True)

    # -------------------------------------------------------------
    # 3. FIVE CORE RESEARCH TABS (Part 5 Specifications)
    # -------------------------------------------------------------
    t_overview, t_financials, t_news, t_ai, t_about = st.tabs([
        "📋 Overview & Valuation",
        "📊 Financial Statements",
        "📰 News & FinBERT",
        "🤖 AI Forecast & Research",
        "🏛️ About & Regulatory Filings"
    ])

    # TAB 1: OVERVIEW & VALUATION
    with t_overview:
        st.markdown("#### Key Valuation & Trading Statistics")
        v1, v2, v3, v4 = st.columns(4)
        with v1:
            st.metric(label="P/E Ratio (Trailing)", value=f"{fundamentals.get('trailing_pe', 'N/A')}")
            st.metric(label="Forward P/E", value=f"{fundamentals.get('forward_pe', 'N/A')}")
        with v2:
            st.metric(label="EPS (Trailing)", value=f"{fundamentals.get('eps', 'N/A')} {currency}")
            st.metric(label="Beta (Volatility)", value=f"{fundamentals.get('beta', 'N/A')}")
        with v3:
            st.metric(label="52-Week High", value=f"{curr_sym}{fundamentals.get('fifty_two_week_high', 'N/A')}")
            st.metric(label="52-Week Low", value=f"{curr_sym}{fundamentals.get('fifty_two_week_low', 'N/A')}")
        with v4:
            st.metric(label="Dividend Yield", value=f"{fundamentals.get('dividend_yield', 0.0) * 100:.2f}%" if isinstance(fundamentals.get('dividend_yield'), (int, float)) else "N/A")
            st.metric(label="Operating Margins", value=f"{fundamentals.get('operating_margins', 0.0) * 100:.1f}%" if isinstance(fundamentals.get('operating_margins'), (int, float)) else "N/A")

    # TAB 2: FINANCIAL STATEMENTS
    with t_financials:
        st.markdown(f"#### Financial Performance ({currency})")
        statements = fundamentals.get("financial_statements", {})
        if statements:
            fin_rows = []
            for k, v in statements.items():
                fin_rows.append({"Metric": k, f"Reported Value ({currency})": v})
            st.dataframe(pd.DataFrame(fin_rows), use_container_width=True)
        else:
            st.info("Detailed audited financial statements table is loading or provider fundamental endpoint is offline.")

    # TAB 3: NEWS & FINBERT SENTIMENT
    with t_news:
        st.markdown("#### Real Financial News & FinBERT Tone Analysis")
        with st.spinner("Analyzing news tone with ProsusAI/finbert transformer..."):
            news_items = fetch_news(ticker, limit=6)

        if news_items:
            for n in news_items:
                sent = n.get("sentiment_label", "Neutral")
                sent_color = "#10b981" if sent == "Positive" else ("#f43f5e" if sent == "Negative" else "#94a3b8")
                st.markdown(f"""
                    <div style="background: #0f172a; border: 1px solid #1e293b; border-radius: 10px; padding: 14px 18px; margin-bottom: 10px;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span style="font-size: 0.8rem; color: #64748b;">{n.get('published_date', 'Recent')} • {n.get('source', 'Financial Wire')}</span>
                            <span style="background: #1e293b; color: {sent_color}; font-size: 0.75rem; font-weight: 700; padding: 2px 8px; border-radius: 12px; border: 1px solid {sent_color};">
                                FinBERT: {sent.upper()}
                            </span>
                        </div>
                        <h4 style="margin: 6px 0; font-size: 1.05rem; color: #f8fafc;">
                            <a href="{n.get('url', '#')}" target="_blank" style="color: #f8fafc; text-decoration: none;">
                                {n.get('title', 'Financial update')} ↗
                            </a>
                        </h4>
                        <p style="color: #94a3b8; font-size: 0.85rem; margin: 0;">{n.get('summary', '')[:200]}...</p>
                    </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No current news articles found for this ticker.")

    # TAB 4: AI FORECAST & RESEARCH (ML + SHAP + Gemini)
    with t_ai:
        st.markdown("#### Machine Learning Directional Forecast & Explainability")
        st.caption("Primary Objective: Predict whether directional return over the next 5 exchange trading sessions will be positive or non-positive.")

        if st.button("🚀 Run Complete Quantitative & Generative AI Synthesis", type="primary", use_container_width=True):
            with st.spinner("Executing ML training, chronological validation, SHAP attribution, and Gemini research synthesis..."):
                analysis_result = run_full_analysis(ticker)
                st.session_state["analysis"] = analysis_result
                st.session_state["active_analysis"] = analysis_result
                st.success("Complete AI pipeline evaluated successfully!")

        analysis = st.session_state.get("analysis")
        if analysis and analysis.get("ticker") == ticker:
            pred = analysis.get("prediction", {})
            metrics = analysis.get("metrics", {})
            training = analysis.get("training", {})

            ai_c1, ai_c2, ai_c3 = st.columns(3)
            with ai_c1:
                st.metric(
                    label="5-Exchange-Session Direction",
                    value=pred.get("direction", "N/A"),
                    delta=f"{pred.get('probability', 0.5):.1%} Model Probability"
                )
            with ai_c2:
                st.metric(
                    label="Champion Model",
                    value=training.get("selected_model", "XGBoost"),
                    delta=f"Val ROC-AUC: {training.get('best_score', 0.0):.3f}"
                )
            with ai_c3:
                st.metric(
                    label="Approach Comparison",
                    value="Hybrid (Tech + Sent)",
                    delta="Approach B Superior" if training.get("hybrid_superior", True) else "Approach A (Quant) Superior"
                )

            # Gemini Synthesis
            st.markdown("##### 🧠 Evidence-Grounded Generative AI Report (Gemini)")
            llm_text = analysis.get("explanation", "")
            if llm_text:
                st.markdown(f"""
                    <div style="background: #0f172a; border: 1px solid #334155; border-radius: 12px; padding: 20px; font-size: 0.95rem; line-height: 1.6; color: #cbd5e1;">
                        {llm_text}
                    </div>
                """, unsafe_allow_html=True)
        else:
            st.info("Click the button above to run the full machine learning prediction, SHAP attribution, and Gemini synthesis for this asset.")

    # TAB 5: ABOUT & REGULATORY FILINGS
    with t_about:
        st.markdown("#### Company Profile & Business Operations")
        st.write(fundamentals.get("description", "Global publicly traded corporation."))

        st.markdown("#### Official Regulatory Filings & Disclosures")
        docs = discover_company_documents(ticker, country)
        if docs:
            for d in docs:
                st.markdown(f"- **{d.get('type', 'Filing')}**: [{d.get('title', 'Regulatory Document')}]({d.get('url', '#')}) ({d.get('date', 'Recent')})")
        else:
            st.caption("No official filing documents catalogued for this asset.")
