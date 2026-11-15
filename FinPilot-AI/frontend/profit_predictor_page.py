"""FinPilot AI — Premium AI Profit Predictor & Investment Simulator UI.

Provides interactive forecasting across 3 core modules:
1. Single Stock AI Profit Predictor (Bearish, Base, Bullish scenarios)
2. Investment Goal Hurdle Simulator (e.g. ₹10,000 to ₹1,00,000)
3. Multi-Stock Portfolio Return & Correlation Simulator
Includes direct virtual paper trading execution and watchlist integration.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from backend.data.company_search import search_companies
from backend.data.global_exchanges import format_currency_amount
from backend.data.market_data import get_latest_price
from backend.ml.goal_simulator import InvestmentGoalSimulator
from backend.ml.portfolio_simulator import MultiStockPortfolioSimulator
from backend.ml.return_forecasting import (
    ReturnForecastingEngine,
    parse_duration_to_trading_days,
)
from backend.trading.paper_engine import PaperTradingEngine, get_fx_rate
from database.db import get_session
from database.models import Watchlist

log = logging.getLogger(__name__)

DURATION_CHOICES = [
    "1 day",
    "1 week",
    "2 weeks",
    "1 month",
    "3 months",
    "6 months",
    "1 year",
    "Custom duration",
]

RISK_CHOICES = ["Conservative (Low)", "Moderate", "Aggressive (High)"]


def render_profit_predictor_page():
    """Render the AI Profit Predictor page."""
    user = st.session_state.get("user")
    if not user:
        st.warning("Please log in to use the AI Profit Predictor.")
        return

    user_id = user["user_id"]
    db = next(get_session())
    try:
        user_summary = PaperTradingEngine.get_user_account_summary(user_id, db)
    finally:
        db.close()

    acc_curr = user_summary.get("account_currency", "INR")
    avail_cash = user_summary.get("available_cash", 100000.0)

    st.markdown("""
        <div style="margin-bottom: 20px;">
            <div style="display: flex; align-items: center; gap: 12px;">
                <span style="font-size: 2.2rem;">📈</span>
                <div>
                    <h1 style="margin: 0; font-size: 1.85rem; font-weight: 800; background: linear-gradient(135deg, #38bdf8, #818cf8); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
                        AI Profit Predictor & Goal Simulator
                    </h1>
                    <span style="color: #94a3b8; font-size: 0.88rem;">
                        Transparent walk-forward return forecasting, risk-calibrated scenarios & goal feasibility modeling.
                    </span>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Top Wallet & Disclaimer Banner
    st.markdown(f"""
        <div style="background: #0f172a; border: 1px solid #1e293b; border-radius: 12px; padding: 12px 18px; margin-bottom: 18px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;">
            <div>
                <span style="color: #64748b; font-size: 0.78rem; text-transform: uppercase; font-weight: 700;">Simulated Account Balance</span>
                <div style="color: #38bdf8; font-size: 1.15rem; font-weight: 800;">{acc_curr} {avail_cash:,.2f}</div>
            </div>
            <div style="font-size: 0.75rem; color: #94a3b8; background: rgba(56, 189, 248, 0.08); border: 1px solid rgba(56, 189, 248, 0.2); padding: 6px 14px; border-radius: 8px;">
                🛡️ <b>100% Virtual Practice Funds</b> — Zero financial risk. Real market historical data.
            </div>
        </div>
    """, unsafe_allow_html=True)

    # 3 Navigation Tabs
    tab1, tab2, tab3 = st.tabs([
        "📊 AI Profit Predictor (Single Asset)",
        "🎯 Goal Hurdle Simulator (₹10k → ₹1L)",
        "💼 Multi-Stock Portfolio Simulator"
    ])

    with tab1:
        _render_single_stock_predictor(user_id, acc_curr, avail_cash)

    with tab2:
        _render_goal_simulator(acc_curr)

    with tab3:
        _render_portfolio_simulator(acc_curr, avail_cash)


# -------------------------------------------------------------------------
# Tab 1: Single Asset AI Profit Predictor
# -------------------------------------------------------------------------
def _render_single_stock_predictor(user_id: int, acc_curr: str, avail_cash: float):
    st.markdown("### 1. How Much Can I Potentially Earn?")
    st.markdown("<p style='color: #94a3b8; font-size: 0.88rem;'>Input your simulated investment parameters to generate validated Bearish, Base, and Bullish forecasts.</p>", unsafe_allow_html=True)

    col_input1, col_input2 = st.columns([1, 1])

    # Pre-select ticker if already selected in Explore
    default_ticker = st.session_state.get("selected_ticker") or st.session_state.get("active_ticker") or "NVDA"

    with col_input1:
        # Question 1: How much money do you want to invest?
        invest_amount = st.number_input(
            f"1. How much money do you want to invest? ({acc_curr})",
            min_value=100.0,
            max_value=10000000.0,
            value=float(min(10000.0, max(1000.0, avail_cash))),
            step=1000.0,
            key="pred_invest_amt",
        )

        # Question 2: Which company or stock do you want to analyse?
        search_query = st.text_input(
            "2. Which company or stock do you want to analyse?",
            value=default_ticker,
            help="Type any global company name or ticker (e.g. NVDA, AAPL, RELIANCE.NS, 7203.T, SIE.DE)",
            key="pred_search_query",
        )

        # Autocomplete search results
        matched_companies = search_companies(search_query, limit=5) if search_query else []
        selected_ticker = default_ticker
        if matched_companies:
            options = [f"{c['ticker']} — {c['name']} ({c['exchange']})" for c in matched_companies]
            chosen_opt = st.selectbox("Select exact match:", options, index=0, key="pred_chosen_company")
            selected_ticker = chosen_opt.split(" — ")[0]
        else:
            selected_ticker = search_query.strip().upper()

    with col_input2:
        # Question 3: Which investment duration do you want?
        dur_choice = st.selectbox(
            "3. Which investment duration do you want?",
            DURATION_CHOICES,
            index=3,  # "1 month" default
            key="pred_dur_choice",
        )
        custom_days = 21
        if dur_choice == "Custom duration":
            custom_days = st.number_input("Custom trading days:", min_value=1, max_value=756, value=45, step=5)
            active_duration = custom_days
        else:
            active_duration = dur_choice

        # Question 4: What is your target amount? (Optional)
        target_amount = st.number_input(
            f"4. What is your target amount? (Optional, in {acc_curr})",
            min_value=0.0,
            max_value=100000000.0,
            value=float(invest_amount * 1.15),
            step=500.0,
            key="pred_target_amt",
        )

        # Question 5: What is your preferred risk level?
        risk_pref = st.selectbox(
            "5. What is your preferred risk level?",
            RISK_CHOICES,
            index=1,  # "Moderate" default
            key="pred_risk_pref",
        )

    # Calculate Forecast Button
    if st.button("🚀 Calculate AI Return & Profit Forecast", use_container_width=True, type="primary"):
        with st.spinner(f"Running chronological walk-forward regression & volatility calibration for {selected_ticker}..."):
            try:
                engine = ReturnForecastingEngine()
                forecast = engine.predict_return_distribution(
                    ticker=selected_ticker,
                    investment_amount=invest_amount,
                    duration=active_duration,
                    target_amount=target_amount if target_amount > invest_amount else None,
                    risk_level=risk_pref.split(" ")[0],
                    account_currency=acc_curr,
                )
                st.session_state["active_forecast"] = forecast
            except Exception as e:
                st.error(f"Could not generate forecast: {e}")
                return

    forecast = st.session_state.get("active_forecast")
    if forecast and forecast.ticker == selected_ticker:
        _display_forecast_results(forecast, user_id, acc_curr, avail_cash)


def _display_forecast_results(fc: Any, user_id: int, acc_curr: str, avail_cash: float):
    st.markdown("---")

    # Header with Quote & Source Transparency
    st.markdown(f"""
        <div style="background: #162238; border: 1px solid #243654; border-radius: 12px; padding: 16px; margin-bottom: 18px;">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
                <div>
                    <h2 style="margin: 0; color: #f8fafc; font-size: 1.35rem; font-weight: 800;">
                        {fc.company_name} ({fc.ticker})
                    </h2>
                    <span style="color: #94a3b8; font-size: 0.8rem;">
                        Current Price: <b>{fc.currency_symbol}{fc.current_price:,.2f} {fc.currency}</b> |
                        Account FX Rate: <b>1 {fc.currency} = {fc.fx_rate_to_account:.4f} {acc_curr}</b>
                    </span>
                </div>
                <div style="text-align: right;">
                    <span style="background: rgba(16, 185, 129, 0.15); color: #10b981; font-size: 0.75rem; font-weight: 700; padding: 4px 10px; border-radius: 6px;">
                        Data Source: {fc.data_source}
                    </span>
                    <div style="color: #64748b; font-size: 0.72rem; margin-top: 4px;">Quote Time: {fc.quote_timestamp[:19]}</div>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    if fc.warning_message:
        st.warning(f"⚠️ {fc.warning_message}")

    # Top 3 High-Level Metric Cards
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Initial Virtual Investment", format_currency_amount(fc.investment_amount, acc_curr))
    with m2:
        st.metric(
            "Base Expected Value",
            fc.base.formatted_ending_value,
            fc.base.formatted_return,
            delta_color="normal" if fc.base.profit_loss >= 0 else "inverse"
        )
    with m3:
        st.metric("Probability of Profit", f"{fc.probability_positive_return:.1%}")
    with m4:
        st.metric("Forecast Uncertainty Band", f"±{fc.forecast_uncertainty_pct:.1f}%")

    st.markdown("#### 2. Three Investment Scenarios (Transparent Projections)")
    st.markdown("<p style='color: #64748b; font-size: 0.78rem;'>*These figures are derived from chronological out-of-sample models and volatility intervals. They are probabilistic scenarios, NOT guaranteed returns.*</p>", unsafe_allow_html=True)

    # 3 Scenario Cards Display
    sc_col1, sc_col2, sc_col3 = st.columns(3)

    with sc_col1:
        st.markdown(f"""
            <div style="background: rgba(244, 63, 94, 0.08); border: 1px solid rgba(244, 63, 94, 0.3); border-radius: 12px; padding: 16px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <span style="color: #f43f5e; font-size: 0.82rem; font-weight: 800; text-transform: uppercase;">🐻 Bearish Scenario</span>
                    <span style="color: #f43f5e; font-weight: 700; font-size: 0.9rem;">{fc.bearish.formatted_return}</span>
                </div>
                <div style="font-size: 1.45rem; font-weight: 800; color: #f8fafc; margin-bottom: 4px;">
                    {fc.bearish.formatted_ending_value}
                </div>
                <div style="color: #f43f5e; font-weight: 600; font-size: 0.85rem; margin-bottom: 8px;">
                    Potential Loss: {fc.bearish.formatted_pl}
                </div>
                <p style="color: #94a3b8; font-size: 0.75rem; margin: 0; line-height: 1.4;">
                    {fc.bearish.description}
                </p>
            </div>
        """, unsafe_allow_html=True)

    with sc_col2:
        st.markdown(f"""
            <div style="background: rgba(56, 189, 248, 0.08); border: 1px solid rgba(56, 189, 248, 0.3); border-radius: 12px; padding: 16px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <span style="color: #38bdf8; font-size: 0.82rem; font-weight: 800; text-transform: uppercase;">⚖️ Base Scenario</span>
                    <span style="color: #38bdf8; font-weight: 700; font-size: 0.9rem;">{fc.base.formatted_return}</span>
                </div>
                <div style="font-size: 1.45rem; font-weight: 800; color: #f8fafc; margin-bottom: 4px;">
                    {fc.base.formatted_ending_value}
                </div>
                <div style="color: #38bdf8; font-weight: 600; font-size: 0.85rem; margin-bottom: 8px;">
                    Estimated Profit: {fc.base.formatted_pl}
                </div>
                <p style="color: #94a3b8; font-size: 0.75rem; margin: 0; line-height: 1.4;">
                    {fc.base.description}
                </p>
            </div>
        """, unsafe_allow_html=True)

    with sc_col3:
        st.markdown(f"""
            <div style="background: rgba(16, 185, 129, 0.08); border: 1px solid rgba(16, 185, 129, 0.3); border-radius: 12px; padding: 16px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <span style="color: #10b981; font-size: 0.82rem; font-weight: 800; text-transform: uppercase;">🐂 Bullish Scenario</span>
                    <span style="color: #10b981; font-weight: 700; font-size: 0.9rem;">{fc.bullish.formatted_return}</span>
                </div>
                <div style="font-size: 1.45rem; font-weight: 800; color: #f8fafc; margin-bottom: 4px;">
                    {fc.bullish.formatted_ending_value}
                </div>
                <div style="color: #10b981; font-weight: 600; font-size: 0.85rem; margin-bottom: 8px;">
                    Potential Profit: {fc.bullish.formatted_pl}
                </div>
                <p style="color: #94a3b8; font-size: 0.75rem; margin: 0; line-height: 1.4;">
                    {fc.bullish.description}
                </p>
            </div>
        """, unsafe_allow_html=True)

    # Professional Scenario Comparison Chart
    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)
    fig = go.Figure()
    scenarios = ["Bearish (Downside)", "Base (Central)", "Bullish (Upside)"]
    ending_vals = [fc.bearish.ending_value, fc.base.ending_value, fc.bullish.ending_value]
    colors = ["#f43f5e", "#38bdf8", "#10b981"]

    fig.add_trace(go.Bar(
        x=scenarios,
        y=ending_vals,
        marker_color=colors,
        text=[format_currency_amount(v, acc_curr) for v in ending_vals],
        textposition="auto",
    ))
    fig.add_hline(
        y=fc.investment_amount,
        line_dash="dot",
        line_color="#fbbf24",
        annotation_text=f"Initial Investment ({format_currency_amount(fc.investment_amount, acc_curr)})",
        annotation_position="bottom right"
    )
    fig.update_layout(
        title=f"Projected Ending Value by Scenario ({fc.investment_duration_label})",
        template="plotly_dark",
        plot_bgcolor="#0f172a",
        paper_bgcolor="#0a0f1d",
        yaxis_title=f"Portfolio Value ({acc_curr})",
        height=350,
        margin=dict(l=20, r=20, t=40, b=20),
    )
    st.plotly_chart(fig, use_container_width=True)

    # Risk Factors & Methodological Transparency
    col_rf, col_mt = st.columns([1, 1])
    with col_rf:
        st.markdown("#### 🚨 Important Risk Factors")
        for rf in fc.risk_factors:
            st.markdown(f"- {rf}")
    with col_mt:
        st.markdown("#### 🔬 Model Evaluation & Transparency")
        for mn in fc.methodology_notes:
            st.markdown(f"- <span style='font-size: 0.82rem; color: #94a3b8;'>{mn}</span>", unsafe_allow_html=True)

    # Paper Trading Execution Action Bar
    st.markdown("---")
    st.markdown("#### 3. Paper Trading & Action Station")
    st.markdown("<p style='color: #94a3b8; font-size: 0.85rem;'>Choose how you would like to proceed with this simulated investment forecast:</p>", unsafe_allow_html=True)

    btn_col1, btn_col2, btn_col3 = st.columns(3)

    with btn_col1:
        if st.button("⭐ Add to Watchlist", use_container_width=True):
            db = next(get_session())
            try:
                exist = db.query(Watchlist).filter(Watchlist.user_id == user_id, Watchlist.ticker == fc.ticker).first()
                if not exist:
                    db.add(Watchlist(
                        user_id=user_id,
                        ticker=fc.ticker,
                        company_name=fc.company_name,
                        currency=fc.currency,
                        country="",
                        exchange="",
                    ))
                    db.commit()
                    st.success(f"Added {fc.ticker} to your virtual watchlist!")
                else:
                    st.info(f"{fc.ticker} is already in your watchlist.")
            finally:
                db.close()

    with btn_col2:
        if st.button("🤖 Ask AI Assistant About This Forecast", use_container_width=True):
            st.session_state["nav"] = "AI Assistant"
            st.rerun()

    with btn_col3:
        # Toggle virtual order placement form
        if st.button("🟢 Proceed to Virtual Buy Order", use_container_width=True, type="primary"):
            st.session_state["show_buy_ticket"] = True

    if st.session_state.get("show_buy_ticket"):
        _render_buy_ticket(fc, user_id, acc_curr, avail_cash)


def _render_buy_ticket(fc: Any, user_id: int, acc_curr: str, avail_cash: float):
    st.markdown("""
        <div style="background: #0f172a; border: 1px solid #10b981; border-radius: 12px; padding: 18px; margin-top: 14px;">
            <h4 style="margin: 0 0 8px 0; color: #10b981;">Simulated Virtual Buy Order Ticket</h4>
            <p style="color: #94a3b8; font-size: 0.82rem; margin-bottom: 12px;">
                Review order parameters before confirming your paper transaction. Zero real-money financial risk.
            </p>
        </div>
    """, unsafe_allow_html=True)

    price_asset = fc.current_price
    fx = fc.fx_rate_to_account
    cost_per_share_acc = price_asset * fx

    shares_est = fc.investment_amount / cost_per_share_acc if cost_per_share_acc > 0 else 0.0

    st.markdown(f"""
        - **Asset**: {fc.company_name} ({fc.ticker})
        - **Live Market Quote**: {fc.currency_symbol}{price_asset:.2f} {fc.currency} ({acc_curr} {cost_per_share_acc:.2f} per share)
        - **Investment Amount**: {acc_curr} {fc.investment_amount:,.2f}
        - **Estimated Shares**: **{shares_est:.4f} shares**
        - **Available Cash Balance**: {acc_curr} {avail_cash:,.2f}
        - **Remaining Cash after Order**: {acc_curr} {max(0.0, avail_cash - fc.investment_amount):,.2f}
    """)

    if avail_cash < fc.investment_amount:
        st.error(f"Insufficient virtual balance ({acc_curr} {avail_cash:,.2f}). Please reduce investment amount or deposit virtual funds in Profile.")
        return

    confirm = st.checkbox("I confirm that I wish to place this simulated virtual paper trading order.", key="confirm_virtual_buy")
    if confirm:
        if st.button("✅ Confirm & Execute Virtual Buy Order", type="primary"):
            db = next(get_session())
            try:
                res = PaperTradingEngine.execute_buy_order(
                    user_id=user_id,
                    ticker=fc.ticker,
                    company_name=fc.company_name,
                    exchange="Global",
                    country="Global",
                    currency=fc.currency,
                    order_type="MARKET",
                    investment_amount_acc=fc.investment_amount,
                    db=db,
                )
                if res.get("success"):
                    st.success(f"🎉 Simulated order executed! Purchased {res.get('quantity'):.4f} shares of {fc.ticker} at {fc.currency_symbol}{res.get('execution_price'):.2f}.")
                    st.balloons()
                    del st.session_state["show_buy_ticket"]
                else:
                    st.error(f"Order failed: {res.get('error')}")
            finally:
                db.close()


# -------------------------------------------------------------------------
# Tab 2: Goal Hurdle Simulator (e.g. ₹10,000 to ₹1,00,000)
# -------------------------------------------------------------------------
def _render_goal_simulator(acc_curr: str):
    st.markdown("### 2. Investment Goal Simulator — ₹10,000 to ₹1,00,000")
    st.markdown("""
        <p style='color: #94a3b8; font-size: 0.88rem;'>
            Understand the exact mathematical compounding hurdles, daily/weekly return rates, and statistical feasibility
            required to transform starting virtual capital into a desired target.
        </p>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        start_cap = st.number_input(
            f"Starting Capital ({acc_curr})",
            min_value=100.0,
            max_value=10000000.0,
            value=10000.0,
            step=1000.0,
            key="goal_start_cap",
        )
    with col2:
        target_cap = st.number_input(
            f"Desired Target ({acc_curr})",
            min_value=start_cap + 100.0,
            max_value=100000000.0,
            value=100000.0,
            step=5000.0,
            key="goal_target_cap",
        )
    with col3:
        time_avail = st.selectbox(
            "Time Available",
            ["1 week", "2 weeks", "1 month", "3 months", "6 months", "1 year"],
            index=2,  # 1 month
            key="goal_time_avail",
        )

    if st.button("🎯 Simulate Goal Feasibility & Hurdle", type="primary"):
        with st.spinner("Calculating compounding hurdles and historical probability distribution..."):
            res = InvestmentGoalSimulator.simulate_goal(
                starting_capital=start_cap,
                target_amount=target_cap,
                time_available=time_avail,
                currency=acc_curr,
            )
            st.session_state["goal_simulation_result"] = res

    goal_res = st.session_state.get("goal_simulation_result")
    if goal_res:
        _display_goal_results(goal_res, acc_curr)


def _display_goal_results(goal_res: Any, acc_curr: str):
    st.markdown("---")
    sel = goal_res.selected_horizon

    # Reality Check Alert
    if goal_res.is_target_extreme:
        st.error(goal_res.extreme_warning)
    else:
        st.success(f"Target Feasibility Rating: **{sel.feasibility_status}** ({sel.risk_verdict})")

    # Metrics
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Capital Multiplier", f"{goal_res.multiple_factor:.1f}x")
    with c2:
        st.metric("Total Gain Required", f"+{goal_res.required_total_return_pct:,.0f}%")
    with c3:
        st.metric("Daily Compounding Rate", f"+{sel.required_daily_compounded_return_pct:.2f}% / day")
    with c4:
        st.metric("Historical Probability", f"{sel.probability_of_reaching_target:.2%}")

    st.markdown("#### Compounding Hurdle Across Diverse Time Horizons")

    # Table of all horizons
    rows = []
    for h in goal_res.all_horizons:
        rows.append({
            "Time Horizon": h.horizon_label,
            "Trading Days": h.trading_sessions,
            "Total Gain %": f"+{h.required_total_return_pct:,.0f}%",
            "Compounded Daily %": f"+{h.required_daily_compounded_return_pct:.2f}%",
            "Compounded Weekly %": f"+{h.required_weekly_compounded_return_pct:.2f}%",
            "Feasibility Status": h.feasibility_status,
            "Historical Probability": f"{h.probability_of_reaching_target:.2%}",
        })
    df_horizons = pd.DataFrame(rows)
    st.dataframe(df_horizons, use_container_width=True)

    # Honest Institutional Advice
    st.markdown("#### 💡 Honest Financial Diagnosis")
    st.info(goal_res.honest_advice)


# -------------------------------------------------------------------------
# Tab 3: Multi-Stock Portfolio Simulator
# -------------------------------------------------------------------------
def _render_portfolio_simulator(acc_curr: str, avail_cash: float):
    st.markdown("### 3. Multi-Stock Investment & Correlation Simulator")
    st.markdown("""
        <p style='color: #94a3b8; font-size: 0.88rem;'>
            Divide your virtual capital across multiple companies and cash.
            Calculates portfolio scenarios using the historical covariance matrix — never independent addition.
        </p>
    """, unsafe_allow_html=True)

    total_cap = st.number_input(
        f"Total Virtual Capital ({acc_curr})",
        min_value=1000.0,
        max_value=100000000.0,
        value=50000.0,
        step=5000.0,
        key="port_total_cap",
    )

    st.markdown("#### Asset Allocations")
    c1, c2 = st.columns(2)
    with c1:
        t1 = st.text_input("Company A Ticker", value="NVDA", key="port_t1")
        a1 = st.number_input(f"Company A Amount ({acc_curr})", min_value=0.0, max_value=total_cap, value=20000.0, step=1000.0, key="port_a1")

        t2 = st.text_input("Company B Ticker", value="AAPL", key="port_t2")
        a2 = st.number_input(f"Company B Amount ({acc_curr})", min_value=0.0, max_value=total_cap, value=15000.0, step=1000.0, key="port_a2")

    with c2:
        t3 = st.text_input("Company C Ticker (Optional)", value="RELIANCE.NS", key="port_t3")
        a3 = st.number_input(f"Company C Amount ({acc_curr})", min_value=0.0, max_value=total_cap, value=10000.0, step=1000.0, key="port_a3")

        time_choice = st.selectbox(
            "Portfolio Investment Horizon",
            ["1 week", "2 weeks", "1 month", "3 months", "6 months", "1 year"],
            index=2,
            key="port_dur_choice",
        )

    allocated_sum = a1 + a2 + a3
    cash_left = max(0.0, total_cap - allocated_sum)

    st.markdown(f"""
        <div style="background: #0f172a; padding: 10px 14px; border-radius: 8px; margin-bottom: 12px; font-size: 0.85rem;">
            Invested in Equities: <b>{acc_curr} {allocated_sum:,.2f}</b> |
            Unallocated Cash: <b style="color: #38bdf8;">{acc_curr} {cash_left:,.2f}</b> ({(cash_left/total_cap)*100:.1f}%)
        </div>
    """, unsafe_allow_html=True)

    if allocated_sum > total_cap:
        st.error("Total allocations exceed your specified virtual capital!")
        return

    if st.button("💼 Run Correlated Portfolio Simulation", type="primary"):
        with st.spinner("Calculating covariance matrix, HHI concentration & portfolio scenarios..."):
            alloc_list = [{"ticker": t1, "amount": a1}, {"ticker": t2, "amount": a2}]
            if t3 and a3 > 0:
                alloc_list.append({"ticker": t3, "amount": a3})

            sim = MultiStockPortfolioSimulator()
            try:
                res = sim.simulate_portfolio(
                    allocations=alloc_list,
                    total_capital=total_cap,
                    duration=time_choice,
                    account_currency=acc_curr,
                )
                st.session_state["active_portfolio_sim"] = res
            except Exception as e:
                st.error(f"Portfolio simulation error: {e}")
                return

    port_res = st.session_state.get("active_portfolio_sim")
    if port_res:
        _display_portfolio_results(port_res, acc_curr)


def _display_portfolio_results(res: Any, acc_curr: str):
    st.markdown("---")
    st.markdown("#### Portfolio Scenarios & Risk Analytics")

    p1, p2, p3, p4 = st.columns(4)
    with p1:
        st.metric("Expected Portfolio Return", f"{res.portfolio_expected_return_pct:+.2f}%")
    with p2:
        st.metric("Base Ending Value", res.base.formatted_ending_value, res.base.formatted_pl)
    with p3:
        st.metric("Annualized Volatility", f"{res.portfolio_annualized_volatility_pct:.1f}%")
    with p4:
        st.metric("Diversification Benefit", f"{res.diversification_benefit_pct:.1f}% vol reduction")

    # 3 Portfolio Scenarios
    sc1, sc2, sc3 = st.columns(3)
    with sc1:
        st.markdown(f"""
            <div style="background: rgba(244, 63, 94, 0.08); border: 1px solid rgba(244, 63, 94, 0.3); border-radius: 10px; padding: 14px;">
                <div style="color: #f43f5e; font-weight: 700; font-size: 0.8rem;">BEARISH PORTFOLIO SCENARIO</div>
                <div style="font-size: 1.35rem; font-weight: 800; color: #f8fafc;">{res.bearish.formatted_ending_value}</div>
                <div style="color: #f43f5e; font-size: 0.85rem; font-weight: 600;">{res.bearish.formatted_pl} ({res.bearish.formatted_return})</div>
            </div>
        """, unsafe_allow_html=True)
    with sc2:
        st.markdown(f"""
            <div style="background: rgba(56, 189, 248, 0.08); border: 1px solid rgba(56, 189, 248, 0.3); border-radius: 10px; padding: 14px;">
                <div style="color: #38bdf8; font-weight: 700; font-size: 0.8rem;">BASE PORTFOLIO SCENARIO</div>
                <div style="font-size: 1.35rem; font-weight: 800; color: #f8fafc;">{res.base.formatted_ending_value}</div>
                <div style="color: #38bdf8; font-size: 0.85rem; font-weight: 600;">{res.base.formatted_pl} ({res.base.formatted_return})</div>
            </div>
        """, unsafe_allow_html=True)
    with sc3:
        st.markdown(f"""
            <div style="background: rgba(16, 185, 129, 0.08); border: 1px solid rgba(16, 185, 129, 0.3); border-radius: 10px; padding: 14px;">
                <div style="color: #10b981; font-weight: 700; font-size: 0.8rem;">BULLISH PORTFOLIO SCENARIO</div>
                <div style="font-size: 1.35rem; font-weight: 800; color: #f8fafc;">{res.bullish.formatted_ending_value}</div>
                <div style="color: #10b981; font-size: 0.85rem; font-weight: 600;">{res.bullish.formatted_pl} ({res.bullish.formatted_return})</div>
            </div>
        """, unsafe_allow_html=True)

    # Exposure & Allocation Visuals
    c_pie1, c_pie2 = st.columns(2)
    with c_pie1:
        # Asset Allocation Donut
        labels = [a.ticker for a in res.assets]
        values = [a.allocated_amount_account for a in res.assets]
        if res.cash_reserved > 0:
            labels.append("Cash Reserve")
            values.append(res.cash_reserved)
        fig_pie = px.pie(names=labels, values=values, title="Portfolio Allocation", hole=0.4)
        fig_pie.update_layout(template="plotly_dark", plot_bgcolor="#0f172a", paper_bgcolor="#0a0f1d", height=280)
        st.plotly_chart(fig_pie, use_container_width=True)

    with c_pie2:
        # Country Exposure Bar
        countries = list(res.country_exposure.keys())
        country_pcts = list(res.country_exposure.values())
        fig_c = px.bar(x=countries, y=country_pcts, title="Country Exposure %", text=country_pcts)
        fig_c.update_layout(template="plotly_dark", plot_bgcolor="#0f172a", paper_bgcolor="#0a0f1d", height=280, yaxis_title="%")
        st.plotly_chart(fig_c, use_container_width=True)

    # Concentration & Correlation details
    st.markdown("#### Concentration & Drawdown Analysis")
    st.markdown(f"""
        - **Herfindahl Concentration Index (HHI)**: **{res.hhi_concentration_index:.1f} / 10,000** ({res.concentration_rating})
        - **Top Holding Weight**: **{res.top_holding_pct:.1f}%**
        - **Estimated Historical Max Drawdown**: **{res.estimated_max_drawdown_pct:.1f}%**
    """)
