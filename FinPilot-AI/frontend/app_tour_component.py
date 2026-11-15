"""FinPilot AI — Interactive Product Tour Walkthrough (Streamlit Component).
Presents the 10 core scenes of the application with interactive navigation,
playback controls, and key educational takeaways.
"""
import streamlit as st

TOUR_SCENES = [
    {
        "id": 1,
        "badge": "🛫 FinPilot v2.0 Global Terminal",
        "title": "Welcome to FinPilot AI",
        "tagline": "Global Multi-Asset Intelligence & Virtual Practice Terminal",
        "desc": "Institutional-grade financial analytics meets accessible paper investing. Research smarter with zero capital risk.",
        "icon": "🛫",
        "points": [
            "Real-time technicals and multi-exchange coverage",
            "Fat-tailed walk-forward machine learning forecasts",
            "100% virtual practice trading with realistic mechanics"
        ]
    },
    {
        "id": 2,
        "badge": "👤 Tailored Experience Tiers",
        "title": "Personalized Investor Onboarding",
        "tagline": "Customized Risk Profiles & Simulated Practice Capital",
        "desc": "Select your experience tier (Beginner, Intermediate, Pro) with tailored tooltips, currency preferences, and virtual practice funds.",
        "icon": "🌱",
        "points": [
            "Beginner: Guided mentorship with plain-English tooltips",
            "Intermediate: Comprehensive ratios and fundamental multiples",
            "Pro Quant: Raw volatility metrics, fat-tail distributions, and beta"
        ]
    },
    {
        "id": 3,
        "badge": "🔍 Global Multi-Asset Discovery",
        "title": "Global Multi-Exchange Stock Search",
        "tagline": "Over 10,000+ Assets Across 22+ World Markets",
        "desc": "Search equities across NASDAQ, NYSE, NSE, BSE, LSE and more with instant live quotes, currency normalization, and FX rates.",
        "icon": "🔍",
        "points": [
            "Instant multi-market search with exchange badges",
            "Live currency conversion to your chosen base currency (INR / USD)",
            "Bid/Ask quotes, daily volume, and market capitalization"
        ]
    },
    {
        "id": 4,
        "badge": "📊 TradingView-Grade Analytics",
        "title": "Interactive Charts & Financial Statements",
        "tagline": "Multi-Timeframe Candlesticks, Moving Averages & RSI",
        "desc": "Deep financial analysis equipped with 20/50 Day SMAs, RSI momentum gauges, MACD signals, balance sheets, and cash flow statements.",
        "icon": "📈",
        "points": [
            "Interactive candlestick, area, and volume charts",
            "Automated moving average crossovers (SMA 20 & SMA 50)",
            "Financial statements: income statements, balance sheets, cash flows"
        ]
    },
    {
        "id": 5,
        "badge": "📈 Walk-Forward ML Scenarios",
        "title": "AI Profit Predictor & Scenario Engine",
        "tagline": "Walk-Forward Return Distributions & Fat-Tailed Calibration",
        "desc": "Enter your investment amount and horizon to project Bearish, Base, and Bullish scenarios, calibrated with Student-t fat-tail intervals.",
        "icon": "🎯",
        "points": [
            "Transparent Bearish (-8%), Base (+5.2%), and Bullish (+12.4%) monetary ranges",
            "Calibrated probability of positive return using walk-forward residuals",
            "Investment Goal Hurdle Simulator: compounding reality checks for ₹10k → ₹1L"
        ]
    },
    {
        "id": 6,
        "badge": "🛡️ Zero-Risk Simulated Wealth",
        "title": "Risk-Free Virtual Money Account",
        "tagline": "100% Simulated Funds for Practical Market Mastery",
        "desc": "Start with ₹1,00,000 or $10,000 in virtual trading capital. Test hypotheses without risking a single rupee of real wealth.",
        "icon": "🛡️",
        "points": [
            "Real-time purchasing power tracking",
            "Dynamic cash vs equity portfolio valuation",
            "Zero real financial risk — learn through safe practice"
        ]
    },
    {
        "id": 7,
        "badge": "🟢 Realistic Trade Tickets",
        "title": "Simulated Market & Limit Orders",
        "tagline": "Realistic Order Execution Safeguards & Slippage",
        "desc": "Place virtual Buy and Sell orders with simulated transaction fees, confirmation checks, and immediate cash balance updates.",
        "icon": "🟢",
        "points": [
            "Market and limit order execution simulation",
            "Realistic slippage modeling (0.05% - 0.10%)",
            "Pre-trade risk confirmation and portfolio impact preview"
        ]
    },
    {
        "id": 8,
        "badge": "💼 Quantitative Risk Dashboard",
        "title": "Portfolio Dashboard & Risk Diagnostics",
        "tagline": "Donut Allocations, HHI Concentration & Drawdowns",
        "desc": "Monitor your holdings with real-time P&L, sector/country diversification breakdowns, HHI concentration indexes, and drawdown metrics.",
        "icon": "💼",
        "points": [
            "Asset allocation donut chart and sector breakdown",
            "Herfindahl-Hirschman Index (HHI) concentration score",
            "Maximum drawdown and portfolio covariance modeling"
        ]
    },
    {
        "id": 9,
        "badge": "🤖 Contextual AI Co-Pilot",
        "title": "24/7 FinPilot AI Financial Mentor",
        "tagline": "Instant Scenario Calculations & Compounding Hurdles",
        "desc": "Ask any question like 'What could ₹10,000 become in 1 month?' to receive instant quantitative tables, goal hurdles, and financial glossaries.",
        "icon": "🤖",
        "points": [
            "Natural language scenario queries: 'What if I invest ₹25,000 in NVDA?'",
            "Honest goal feasibility checks: required daily compounding hurdles",
            "Contextual financial term explanations and beginner tutorials"
        ]
    },
    {
        "id": 10,
        "badge": "🧠 Explainable AI Intelligence",
        "title": "FinBERT Sentiment & SHAP Explainability",
        "tagline": "Transparent Transformer Scores & Evidence Retrieval",
        "desc": "Understand the 'why' behind stock forecasts with Transformer-based FinBERT sentiment, RAG SEC citations, and SHAP feature importance.",
        "icon": "🧠",
        "points": [
            "FinBERT financial tone analysis on earnings releases and news",
            "SHAP explainability: top feature drivers (revenue growth, momentum, interest rates)",
            "RAG citations from public SEC 10-K and 10-Q disclosures"
        ]
    }
]


def render_app_tour_modal():
    """Renders the interactive product walkthrough tour overlay."""
    if "tour_scene_idx" not in st.session_state:
        st.session_state["tour_scene_idx"] = 0

    idx = st.session_state["tour_scene_idx"]
    scene = TOUR_SCENES[idx]
    total_scenes = len(TOUR_SCENES)

    st.markdown("""
        <div style="background: linear-gradient(135deg, #0f172a, #1e1b4b); border: 2px solid #38bdf8; border-radius: 16px; padding: 20px; margin-bottom: 24px; box-shadow: 0 10px 25px -5px rgba(56, 189, 248, 0.2);">
    """, unsafe_allow_html=True)

    # Top Bar: Title & Skip Intro
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown(f"""
            <span style="font-size: 0.75rem; font-weight: 800; color: #38bdf8; text-transform: uppercase; letter-spacing: 0.05em; background: rgba(56,189,248,0.15); padding: 3px 10px; border-radius: 999px;">
                {scene['badge']}
            </span>
            <h2 style="color: #ffffff; font-size: 1.5rem; font-weight: 800; margin: 8px 0 2px 0;">
                {scene['icon']} {scene['title']}
            </h2>
            <p style="color: #94a3b8; font-size: 0.88rem; margin: 0;">{scene['tagline']}</p>
        """, unsafe_allow_html=True)

    with col2:
        if st.button("⏩ Skip Intro", key="tour_skip_btn", use_container_width=True):
            st.session_state["show_app_tour"] = False
            st.session_state["tour_scene_idx"] = 0
            st.rerun()

    # Progress Bar
    progress_val = (idx + 1) / total_scenes
    st.progress(progress_val)
    st.caption(f"Scene {idx + 1} of {total_scenes} • 35-Second Guided Product Glimpse")

    # Scene Description & Features
    st.markdown(f"""
        <div style="background: #1e293b; border-radius: 12px; padding: 16px; margin: 12px 0; border: 1px solid #334155;">
            <p style="color: #e2e8f0; font-size: 0.95rem; line-height: 1.6; margin-bottom: 12px;">
                {scene['desc']}
            </p>
            <ul style="color: #94a3b8; font-size: 0.88rem; line-height: 1.6; padding-left: 20px; margin: 0;">
                {''.join(f"<li><b style='color:#f8fafc'>{p.split(':')[0]}</b>{':' + p.split(':')[1] if ':' in p else ''}</li>" for p in scene['points'])}
            </ul>
        </div>
    """, unsafe_allow_html=True)

    # Outro Callout on Final Scene
    if idx == total_scenes - 1:
        st.markdown("""
            <div style="background: linear-gradient(135deg, rgba(56,189,248,0.2), rgba(129,140,248,0.2)); border: 1px solid #818cf8; border-radius: 12px; padding: 14px; text-align: center; margin: 12px 0;">
                <h3 style="color: #ffffff; font-weight: 800; font-size: 1.05rem; margin: 0 0 4px 0;">
                    "Research Smarter. Practise Investing. Understand Your Money. Powered by FinPilot AI."
                </h3>
                <span style="color: #94a3b8; font-size: 0.78rem;">Zero Real Money Risk • Institutional Analytics • Accessible Learning</span>
            </div>
        """, unsafe_allow_html=True)

    # Navigation Controls
    btn_col1, btn_col2, btn_col3, btn_col4 = st.columns([1, 1, 1, 2])
    with btn_col1:
        if st.button("◀ Previous", disabled=(idx == 0), key="tour_prev_btn", use_container_width=True):
            st.session_state["tour_scene_idx"] = max(0, idx - 1)
            st.rerun()

    with btn_col2:
        if st.button("↺ Replay", key="tour_replay_btn", use_container_width=True):
            st.session_state["tour_scene_idx"] = 0
            st.rerun()

    with btn_col3:
        if idx < total_scenes - 1:
            if st.button("Next ▶", key="tour_next_btn", use_container_width=True):
                st.session_state["tour_scene_idx"] = idx + 1
                st.rerun()
        else:
            if st.button("Finish Tour 🚀", key="tour_finish_btn", use_container_width=True):
                st.session_state["show_app_tour"] = False
                st.session_state["tour_scene_idx"] = 0
                st.rerun()

    with btn_col4:
        st.markdown(f"<div style='text-align: right; padding-top: 6px; font-size: 0.8rem; color: #64748b; font-family: monospace;'>⏱ ~{int(progress_val * 35)}s / 35s</div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)
