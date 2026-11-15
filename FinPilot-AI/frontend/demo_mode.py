"""FinPilot AI — Recruiter & Evaluator Fintech Demo Mode.

Provides a fully populated demonstration environment showcasing all institutional
capabilities (portfolio, risk analytics, backtesting, AI forecasting) in seconds
without requiring manual trading setup. All demo data is strictly labeled.
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

DEMO_HOLDINGS = [
    {"Ticker": "NVDA", "Name": "NVIDIA Corporation", "Sector": "Technology", "Shares": 20, "Avg Cost": "$115.00", "Current Price": "$128.50", "Value (INR)": "₹2,14,595", "Unrealized P&L": "+11.7%", "Weight": "35.0%"},
    {"Ticker": "AAPL", "Name": "Apple Inc.", "Sector": "Technology", "Shares": 15, "Avg Cost": "$210.00", "Current Price": "$224.30", "Value (INR)": "₹2,80,375", "Unrealized P&L": "+6.8%", "Weight": "25.0%"},
    {"Ticker": "RELIANCE.NS", "Name": "Reliance Industries", "Sector": "Energy", "Shares": 50, "Avg Cost": "₹2,850.00", "Current Price": "₹2,980.50", "Value (INR)": "₹1,49,025", "Unrealized P&L": "+4.6%", "Weight": "20.0%"},
    {"Ticker": "MSFT", "Name": "Microsoft Corporation", "Sector": "Technology", "Shares": 5, "Avg Cost": "$410.00", "Current Price": "$425.20", "Value (INR)": "₹1,77,208", "Unrealized P&L": "+3.7%", "Weight": "15.0%"},
    {"Ticker": "CASH", "Name": "Virtual Cash Reserve", "Sector": "Cash", "Shares": "-", "Avg Cost": "-", "Current Price": "-", "Value (INR)": "₹45,000", "Unrealized P&L": "0.0%", "Weight": "5.0%"},
]


def render_demo_mode():
    """Render fast-track demonstration environment for project evaluators."""
    # Prominent Recruiter Demo Header
    st.markdown("""
        <div style="background: linear-gradient(135deg, rgba(245, 158, 11, 0.15), rgba(56, 189, 248, 0.15)); border: 2px solid #f59e0b; border-radius: 16px; padding: 20px; margin-bottom: 24px;">
            <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px;">
                <div>
                    <span style="font-size: 0.75rem; font-weight: 800; color: #f59e0b; text-transform: uppercase; letter-spacing: 0.08em; background: rgba(245, 158, 11, 0.2); padding: 4px 10px; border-radius: 999px;">
                        ⚠️ EVALUATOR DEMO MODE ACTIVE
                    </span>
                    <h2 style="color: #ffffff; font-size: 1.6rem; font-weight: 800; margin: 8px 0 2px 0;">
                        Recruiter & Evaluator Fast-Track Overview
                    </h2>
                    <p style="color: #cbd5e1; font-size: 0.88rem; margin: 0;">
                        Pre-populated institutional portfolio showcasing all 10+ FinPilot AI modules with zero configuration.
                    </p>
                </div>
                <div style="text-align: right;">
                    <span style="font-size: 0.8rem; font-weight: 700; color: #94a3b8;">Sample Virtual Portfolio Worth</span>
                    <div style="font-size: 1.5rem; font-weight: 800; color: #10b981; font-family: monospace;">₹8,66,203</div>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Fast-Navigation Buttons
    st.markdown("### 🚀 Fast-Track Feature Jump")
    n1, n2, n3, n4 = st.columns(4)
    with n1:
        if st.button("📈 AI Profit Predictor", use_container_width=True):
            st.session_state["nav"] = "Profit Predictor"
            st.rerun()
    with n2:
        if st.button("⚡ Risk Analytics", use_container_width=True):
            st.session_state["nav"] = "Risk Analytics"
            st.rerun()
    with n3:
        if st.button("🔬 Quant Research Lab", use_container_width=True):
            st.session_state["nav"] = "Quant Lab"
            st.rerun()
    with n4:
        if st.button("📉 Strategy Backtesting", use_container_width=True):
            st.session_state["nav"] = "Backtesting"
            st.rerun()

    # Section 1: Pre-Populated Portfolio
    st.markdown("### 💼 Sample Institutional Portfolio")
    st.dataframe(pd.DataFrame(DEMO_HOLDINGS), use_container_width=True, hide_index=True)

    # Section 2: Core Highlights Grid
    c_left, c_right = st.columns(2)

    with c_left:
        st.markdown("### 🎯 Key Engineering Highlights")
        st.markdown("""
        - **Return Magnitude Forecaster**: Walk-forward ensemble combining Random Forest Regressor & Ridge with Student-t fat-tail intervals.
        - **Compounding Hurdle Engine**: Exact mathematical compounding checks for ambitious targets (e.g. ₹10k to ₹1L).
        - **Strict Look-Ahead Bias Prevention**: Backtesting signals at Close(t) execute at Open(t+1) with realistic slippage.
        - **Multi-Exchange Coverage**: Real-time quotes and fundamentals across 22+ global exchanges with live FX conversion.
        - **Explainable AI (XAI)**: SHAP game-theoretic Shapley values and FinBERT Transformer sentiment tone analysis.
        """)

    with c_right:
        st.markdown("### 📊 Sample Multi-Asset Donut Breakdown")
        fig_demo = go.Figure(data=[go.Pie(
            labels=["NVDA (35%)", "AAPL (25%)", "RELIANCE (20%)", "MSFT (15%)", "Cash (5%)"],
            values=[35, 25, 20, 15, 5],
            hole=0.55,
            marker_colors=["#38bdf8", "#818cf8", "#10b981", "#f59e0b", "#94a3b8"]
        )])
        fig_demo.update_layout(
            template="plotly_dark",
            plot_bgcolor="#0f172a",
            paper_bgcolor="#0f172a",
            margin=dict(l=0, r=0, t=10, b=0),
            height=240,
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
        )
        st.plotly_chart(fig_demo, use_container_width=True)

    st.caption("🛡️ **Demonstration Data Notice**: All metrics on this page are pre-loaded sample records for evaluator inspection. Your personal account data remains completely private and isolated.")
