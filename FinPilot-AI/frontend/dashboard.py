"""Universal Global Dashboard for FinPilot AI."""
import streamlit as st
import plotly.graph_objects as go
from backend.services.analysis_service import run_full_analysis
from backend.data.company_search import search_global_companies, BENCHMARK_COMPANIES
from backend.data.global_exchanges import format_currency_amount, get_exchange_info, CURRENCY_SYMBOLS
from database.db import SessionLocal
from database.models import AnalysisHistory


def render_dashboard():
    """Render the universal executive overview dashboard."""
    st.markdown("""
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 1.2rem;">
            <div>
                <h1 style="margin: 0; font-size: 2.2rem; font-weight: 800; letter-spacing: -0.02em;">
                    ◈ FinPilot AI — Global Financial Intelligence
                </h1>
                <p style="margin: 4px 0 0 0; color: #94a3b8; font-size: 1rem;">
                    Universal Multi-Market Financial Prediction, FinBERT Sentiment & Explainable AI
                </p>
            </div>
        </div>
    """, unsafe_allow_html=True)

    st.info(
        "⚖️ **Global Research Disclaimer:** FinPilot AI is an educational financial intelligence platform covering publicly "
        "listed companies worldwide. Directional forecasts and probabilities are empirical statistical model estimates, "
        "not guaranteed outcomes or personalized investment advice. All assets trade in their native exchange currencies."
    )

    # -------------------------------------------------------------
    # Global Company Search Engine Section
    # -------------------------------------------------------------
    st.markdown("### 🌐 Universal Company Search & Exchange Discovery")

    # Search Bar & Parameter Controls
    c_search, c_country, c_period = st.columns([4, 2, 2])
    
    with c_search:
        search_query = st.text_input(
            "Search by Company Name, Ticker, or Exchange",
            value=st.session_state.get("search_query", st.session_state.get("ticker", "NVDA")),
            placeholder="e.g. Reliance, Toyota, Siemens, Samsung, Apple, NVDA, 7203.T, RELIANCE.NS",
            help="Enter any global company name, local ticker, or international ticker symbol.",
        )

    with c_country:
        country_filter = st.selectbox(
            "Filter by Country / Region",
            options=[
                "All Global Markets",
                "United States",
                "India",
                "Japan",
                "Germany",
                "United Kingdom",
                "South Korea",
                "Hong Kong / China",
                "Australia",
                "Canada",
                "Switzerland",
                "Saudi Arabia",
            ],
            index=0,
        )

    with c_period:
        period_val = st.selectbox(
            "Market History Window",
            options=["2y", "5y", "10y"],
            index=1,
            help="Historical window for chronological model training and technical indicators.",
        )

    # Global Quick Select Shortcuts
    st.markdown("<p style='font-size: 0.85rem; color: #64748b; margin-top: -6px; margin-bottom: 8px;'><b>Global Benchmarks:</b> "
                "🇺🇸 <a href='javascript:void(0)' style='color:#38bdf8;'>NVDA</a> | "
                "🇮🇳 <a href='javascript:void(0)' style='color:#38bdf8;'>RELIANCE.NS</a> | "
                "🇯🇵 <a href='javascript:void(0)' style='color:#38bdf8;'>7203.T (Toyota)</a> | "
                "🇰🇷 <a href='javascript:void(0)' style='color:#38bdf8;'>005930.KS (Samsung)</a> | "
                "🇩🇪 <a href='javascript:void(0)' style='color:#38bdf8;'>SIE.DE (Siemens)</a> | "
                "🇬🇧 <a href='javascript:void(0)' style='color:#38bdf8;'>HSBA.L (HSBC)</a> | "
                "🇦🇺 <a href='javascript:void(0)' style='color:#38bdf8;'>BHP.AX</a> | "
                "🇸🇦 <a href='javascript:void(0)' style='color:#38bdf8;'>2222.SR (Aramco)</a></p>",
                unsafe_allow_html=True)

    # Dynamic Search Matches with Disambiguation
    c_filter_str = None if country_filter == "All Global Markets" else country_filter
    matches = search_global_companies(search_query, country_filter=c_filter_str, limit=6)

    selected_ticker = search_query.strip().upper()

    if matches:
        with st.expander(f"🔍 Discovered Global Matches for '{search_query}' ({len(matches)} found — click to select)", expanded=False):
            cols = st.columns(min(len(matches), 3))
            for i, m in enumerate(matches):
                col = cols[i % 3]
                with col:
                    flag = m.get("flag", "🌐")
                    t = m["ticker"]
                    name = m["name"]
                    exc = m.get("exchange", "")
                    cntry = m.get("country", "")
                    curr = m.get("currency", "USD")
                    
                    st.markdown(f"""
                        <div style="background: #162238; border: 1px solid #243654; border-radius: 8px; padding: 10px; margin-bottom: 8px;">
                            <div style="font-weight: 700; color: #38bdf8; font-size: 1rem;">{flag} {t}</div>
                            <div style="font-size: 0.82rem; color: #f8fafc; font-weight: 600;">{name[:32]}</div>
                            <div style="font-size: 0.75rem; color: #94a3b8;">{exc} • {cntry} • {curr}</div>
                        </div>
                    """, unsafe_allow_html=True)
                    if st.button(f"Analyze {t}", key=f"btn_match_{t}_{i}", use_container_width=True):
                        selected_ticker = t
                        st.session_state["ticker"] = t
                        st.session_state["search_query"] = t
                        st.rerun()

    # Trigger Analysis Button
    col_btn, _ = st.columns([3, 5])
    with col_btn:
        analyze_clicked = st.button("🚀 Run Comprehensive Global Analysis", type="primary", use_container_width=True)

    if analyze_clicked:
        target_ticker = st.session_state.get("ticker", selected_ticker)
        if not target_ticker:
            st.error("Please enter or select a valid company or ticker symbol.")
        else:
            with st.spinner(f"Executing quantitative ML, FinBERT sentiment, RAG, and SHAP pipeline for {target_ticker}..."):
                try:
                    result = run_full_analysis(target_ticker, period=period_val, run_llm=True)
                    st.session_state["analysis"] = result
                    st.session_state["ticker"] = target_ticker
                    st.success(f"Analysis completed successfully for {target_ticker} ({result.get('company_name', target_ticker)})!")
                except Exception as exc:
                    st.error(f"Analysis Failed: {exc}")

    # -------------------------------------------------------------
    # Active Asset Display Section
    # -------------------------------------------------------------
    analysis = st.session_state.get("analysis")
    if analysis:
        st.markdown("<hr style='border-color: #243654; margin: 1.5rem 0;'>", unsafe_allow_html=True)

        fundamentals = analysis.get("fundamentals", {})
        price_info = analysis.get("latest_price", {})
        pred = analysis.get("prediction", {})
        training = analysis.get("training", {})
        sentiment = analysis.get("sentiment", {})
        market_df = analysis.get("market")

        curr_code = analysis.get("currency", "USD")
        curr_sym = analysis.get("currency_symbol", CURRENCY_SYMBOLS.get(curr_code, curr_code))
        flag = analysis.get("flag", "🌐")
        exchange_name = analysis.get("exchange", "Exchange")
        country_name = analysis.get("country", "Global")
        comp_name = analysis.get("company_name", analysis["ticker"])
        last_date = analysis.get("last_market_date", "Latest")

        close_price = price_info.get("close", 0.0)
        formatted_close = format_currency_amount(close_price, curr_code)
        change_val = price_info.get("change", 0.0)
        formatted_change = price_info.get("formatted_change") or f"{change_val:+.2f}"
        change_pct_val = price_info.get("change_pct", 0.0)
        change_color = "#34d399" if change_val >= 0 else "#fb7185"

        # Global Company Header Card
        st.markdown(f"""
            <div class="finpilot-card" style="margin-bottom: 1.5rem; background: #0f172a; border: 1px solid #1e293b; border-radius: 12px; padding: 20px;">
                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;">
                    <div>
                        <div style="display: flex; align-items: center; gap: 8px;">
                            <span style="font-size: 1.8rem;">{flag}</span>
                            <h2 style="margin: 0; font-size: 1.8rem; font-weight: 800; color: #f8fafc;">
                                {comp_name} ({analysis['ticker']})
                            </h2>
                        </div>
                        <div style="color: #94a3b8; font-size: 0.9rem; margin-top: 6px;">
                            Country: <b>{country_name}</b> &nbsp;|&nbsp; 
                            Exchange: <b>{exchange_name}</b> &nbsp;|&nbsp; 
                            Trading Currency: <b>{curr_code} ({curr_sym})</b> &nbsp;|&nbsp; 
                            Sector: <b>{fundamentals.get('sector', 'N/A')}</b> &nbsp;|&nbsp; 
                            Last Session: <b>{last_date}</b>
                        </div>
                    </div>
                    <div style="text-align: right;">
                        <span style="font-size: 2rem; font-weight: 800; color: #38bdf8;">
                            {formatted_close}
                        </span>
                        <div style="font-size: 1rem; font-weight: 600; color: {change_color};">
                            {formatted_change} ({change_pct_val:+.2f}%)
                        </div>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)

        # Quick Action Action Bar: Paper Trade, Ask AI, Add to Watchlist
        qa1, qa2, qa3, qa4 = st.columns([1.2, 1.4, 1.2, 2.2])
        with qa1:
            if st.button("🟢 Trade Virtually", use_container_width=True, type="primary"):
                st.session_state["active_ticker"] = analysis["ticker"]
                st.session_state["nav"] = "Virtual Investing"
                st.rerun()
        with qa2:
            if st.button("🤖 Ask AI About This Stock", use_container_width=True):
                st.session_state["active_analysis"] = analysis
                st.session_state["nav"] = "AI Financial Assistant"
                st.rerun()
        with qa3:
            if st.button("⭐ Watchlist", use_container_width=True):
                st.session_state["active_ticker"] = analysis["ticker"]
                st.session_state["nav"] = "Watchlist"
                st.rerun()
        with qa4:
            st.caption("🛡️ Simulated Practice Trading: Live market prices with fake currency.")

        # Top Executive Metrics Row
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.metric(
                label=f"Latest Close ({curr_code})",
                value=formatted_close,
                delta=f"{price_info.get('change_pct', 0.0):+.2f}% ({exchange_name} Session)",
            )
        with m2:
            direction = pred.get("direction", "N/A")
            is_pos = "Positive" in direction
            st.metric(
                label="5-Exchange-Session Forecast",
                value=direction,
                delta="Bullish Outlook" if is_pos else "Bearish / Neutral",
                delta_color="normal" if is_pos else "inverse",
            )
        with m3:
            conf = pred.get("probability", 0.0)
            st.metric(
                label="Model Confidence",
                value=f"{conf:.1%}",
                delta=f"Selected: {training.get('selected_model', 'Best')}",
            )
        with m4:
            sent_label = sentiment.get("overall_label", "N/A") if sentiment.get("available") else "Offline"
            st.metric(
                label="FinBERT Sentiment",
                value=sent_label,
                delta=f"Score: {sentiment.get('score', 0.0):+.2f}" if sentiment.get("available") else "No Articles",
            )

        # Historical Market Performance Chart in Native Currency
        if market_df is not None and not market_df.empty:
            st.markdown(f"### Historical Market Performance ({curr_code})")
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=market_df.index,
                y=market_df["Close"],
                mode="lines",
                name=f"Close Price ({curr_code})",
                line=dict(color="#38bdf8", width=2),
                fill="tozeroy",
                fillcolor="rgba(56, 189, 248, 0.08)",
            ))
            fig.update_layout(
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                height=380,
                margin=dict(l=0, r=0, t=10, b=0),
                xaxis=dict(showgrid=True, gridcolor="#1e293b", title="Trading Session Date"),
                yaxis=dict(showgrid=True, gridcolor="#1e293b", tickprefix=curr_sym, title=f"Price ({curr_code})"),
            )
            st.plotly_chart(fig, use_container_width=True)

    # -------------------------------------------------------------
    # Recent Global Analysis History (Persisted in SQLite)
    # -------------------------------------------------------------
    st.markdown("### 📜 Recent Global Analysis Audit Trail")
    db = SessionLocal()
    try:
        past = db.query(AnalysisHistory).order_by(AnalysisHistory.analysis_date.desc()).limit(8).all()
        if past:
            records = []
            for p in past:
                flag_p = get_exchange_info(getattr(p, "exchange", "") or p.ticker).flag
                records.append({
                    "Date (UTC)": p.analysis_date.strftime("%Y-%m-%d %H:%M") if p.analysis_date else "N/A",
                    "Asset": f"{flag_p} {p.ticker}",
                    "Company": p.company_name or p.ticker,
                    "Country": getattr(p, "country", "Global") or "Global",
                    "Exchange": getattr(p, "exchange", "N/A") or "N/A",
                    "Currency": getattr(p, "currency", "USD") or "USD",
                    "5D Forecast": p.prediction_summary,
                    "Sentiment": p.sentiment_summary,
                    "Model": p.selected_model or "Best Model",
                })
            st.dataframe(records, use_container_width=True, hide_index=True)
        else:
            st.caption("No previous analysis history stored yet. Run an analysis above to persist results.")
    finally:
        db.close()
