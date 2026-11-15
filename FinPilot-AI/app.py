"""FinPilot AI — Premium Global Trading & AI Platform.
Inspired by Groww simplicity and TradingView analytical depth.
"""
import streamlit as st
from config.settings import settings
from config.logging_config import configure_logging
from database.db import init_db, get_session
from backend.trading.paper_engine import PaperTradingEngine

# Frontend Pages & Components
from frontend.auth_component import render_auth_modal, render_onboarding_flow
from frontend.home_page import render_home_page
from frontend.company_detail_page import render_company_detail_page
from frontend.watchlist_page import render_watchlist_page
from frontend.portfolio_page import render_portfolio_page
from frontend.virtual_investing_page import render_virtual_investing_page
from frontend.ai_assistant_page import render_ai_assistant_page
from frontend.learning_page import render_learning_page
from frontend.profile_page import render_profile_page
from frontend.profit_predictor_page import render_profit_predictor_page
from frontend.app_tour_component import render_app_tour_modal
from frontend.market_overview_page import render_market_overview_page
from frontend.quant_research_lab import render_quant_research_lab
from frontend.risk_analytics_dashboard import render_risk_analytics_dashboard
from frontend.backtesting_lab import render_backtesting_lab
from frontend.model_monitoring import render_model_monitoring
from frontend.data_quality_monitor import render_data_quality_monitor
from frontend.portfolio_terminal import render_portfolio_terminal
from frontend.stock_screener_page import render_stock_screener_page
from frontend.demo_mode import render_demo_mode
from frontend.styles import apply_styles

# Page configuration
st.set_page_config(
    page_title="FinPilot AI — Global Investing & AI Mentorship",
    page_icon="🛫",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize application dependencies
configure_logging()
init_db()
apply_styles()

# -------------------------------------------------------------
# User Authentication & Evaluator Fast-Track Gate
# -------------------------------------------------------------
if "user" not in st.session_state:
    st.session_state["user"] = None

user = st.session_state["user"]

if not user:
    # Check if guest demo mode was requested
    if st.session_state.get("guest_demo_mode"):
        user = {
            "user_id": 1,
            "name": "Guest Evaluator",
            "email": "evaluator@finpilot.ai",
            "experience_level": "Pro Quant",
            "preferred_currency": "INR",
            "onboarding_completed": True,
        }
        st.session_state["user"] = user
    else:
        # Show Auth modal with Demo Guest Quick Login Option
        col_m1, col_m2 = st.columns([3, 1])
        with col_m2:
            if st.button("🚀 Enter Guest Demo Mode", use_container_width=True, help="Explore FinPilot AI immediately as an evaluator"):
                st.session_state["guest_demo_mode"] = True
                st.rerun()
        render_auth_modal()
        st.stop()

if not user.get("onboarding_completed") or st.session_state.get("trigger_onboarding"):
    render_onboarding_flow(user)
    st.stop()


# -------------------------------------------------------------
# Comprehensive Institutional Fintech Navigation Suite
# -------------------------------------------------------------
PAGES = {
    "Home": {"func": render_home_page, "icon": "🏠", "desc": "Executive portfolio snapshot & market overview"},
    "Global Markets": {"func": render_market_overview_page, "icon": "🌍", "desc": "Global exchange benchmark indices"},
    "Stock Screener": {"func": render_stock_screener_page, "icon": "🔎", "desc": "Multi-exchange fundamental & technical screener"},
    "Explore": {"func": render_company_detail_page, "icon": "🔍", "desc": "Global company research & interactive charts"},
    "Profit Predictor": {"func": render_profit_predictor_page, "icon": "📈", "desc": "AI return forecasts, scenarios & goal simulator"},
    "Orders": {"func": render_virtual_investing_page, "icon": "🟢", "desc": "Simulated order ticket & trade execution"},
    "Portfolio": {"func": render_portfolio_page, "icon": "💼", "desc": "Holdings, allocation & concentration risk"},
    "Portfolio Terminal": {"func": render_portfolio_terminal, "icon": "📊", "desc": "Advanced portfolio analytics & CSV data export"},
    "Risk Analytics": {"func": render_risk_analytics_dashboard, "icon": "⚡", "desc": "VaR, CVaR, Sharpe, stress testing & covariance"},
    "Quant Lab": {"func": render_quant_research_lab, "icon": "🔬", "desc": "Rolling volatility, beta regression & drawdowns"},
    "Backtesting": {"func": render_backtesting_lab, "icon": "📉", "desc": "Historical strategy testing with anti-leakage safeguards"},
    "Model Monitor": {"func": render_model_monitoring, "icon": "🤖", "desc": "ML governance, model cards & drift audit"},
    "Data Quality": {"func": render_data_quality_monitor, "icon": "📡", "desc": "Provider health, data freshness & provenance"},
    "Watchlist": {"func": render_watchlist_page, "icon": "⭐", "desc": "Target company monitor & price alerts"},
    "AI Assistant": {"func": render_ai_assistant_page, "icon": "🤖", "desc": "24/7 intelligent financial mentor"},
    "Learn": {"func": render_learning_page, "icon": "🎓", "desc": "Beginner lessons, quizzes & glossary"},
    "Demo Mode": {"func": render_demo_mode, "icon": "🎯", "desc": "Recruiter demo with pre-populated portfolio"},
    "Profile": {"func": render_profile_page, "icon": "👤", "desc": "Account funds, experience & credentials"},
}

# Programmatic navigation handling
if "nav" in st.session_state and st.session_state["nav"] in PAGES:
    nav_index = list(PAGES.keys()).index(st.session_state["nav"])
    del st.session_state["nav"]
else:
    nav_index = 0

# Fetch user virtual balance for sidebar badge
db = next(get_session())
try:
    user_summary = PaperTradingEngine.get_user_account_summary(user["user_id"], db)
finally:
    db.close()

user_curr = user_summary.get("account_currency", "INR")
user_cash = user_summary.get("available_cash", 100000.0)
user_worth = user_summary.get("total_portfolio_value", 100000.0)

# Sidebar Header & User Profile Card
with st.sidebar:
    st.markdown("""
        <div style="padding: 4px 0 14px 0;">
            <div style="display: flex; align-items: center; gap: 10px;">
                <span style="font-size: 2rem;">🛫</span>
                <div>
                    <h2 style="margin: 0; font-size: 1.45rem; font-weight: 800; background: linear-gradient(135deg, #38bdf8, #818cf8); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
                        FinPilot AI
                    </h2>
                    <span style="color: #64748b; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.5px; font-weight: 700;">
                        Global Trading Terminal
                    </span>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Groww-style User Wallet & Profile Badge
    st.markdown(f"""
        <div style="background: #0f172a; border: 1px solid #1e293b; border-radius: 12px; padding: 14px; margin-bottom: 14px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                <span style="font-size: 0.88rem; font-weight: 700; color: #f8fafc;">👤 {user.get('name', 'Investor')}</span>
                <span style="background: rgba(56, 189, 248, 0.15); color: #38bdf8; font-size: 0.72rem; font-weight: 700; padding: 2px 8px; border-radius: 10px;">
                    {user.get('experience_level', 'Beginner')}
                </span>
            </div>
            <div style="color: #94a3b8; font-size: 0.8rem; line-height: 1.5;">
                Virtual Cash: <b style="color: #38bdf8;">{user_curr} {user_cash:,.2f}</b><br>
                Portfolio: <b style="color: #10b981;">{user_curr} {user_worth:,.2f}</b>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Active Asset Status Indicator (if asset selected)
    active_ticker = st.session_state.get("selected_ticker") or st.session_state.get("active_ticker")
    if active_ticker:
        st.markdown(f"""
            <div style="background: #162238; border: 1px solid #243654; border-radius: 8px; padding: 8px 12px; margin-bottom: 12px; display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <div style="font-size: 0.7rem; color: #64748b; text-transform: uppercase;">Active Asset</div>
                    <b style="color: #f8fafc; font-size: 0.95rem;">{active_ticker}</b>
                </div>
                <span style="color: #38bdf8; font-size: 0.8rem; font-weight: 600;">Selected</span>
            </div>
        """, unsafe_allow_html=True)

    st.markdown("<p style='font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em; color: #64748b; font-weight: 700; margin-bottom: 4px;'>Menu</p>", unsafe_allow_html=True)

    page_options = list(PAGES.keys())
    page_labels = {p: f"{PAGES[p]['icon']}  {p}" for p in page_options}

    selected_page = st.radio(
        "Navigation",
        options=page_options,
        index=nav_index,
        format_func=lambda p: page_labels[p],
        label_visibility="collapsed",
    )

    st.markdown("<hr style='border-color: #243654; margin: 18px 0 10px 0;'>", unsafe_allow_html=True)

    # Fast Action Button: Ask AI Assistant
    if st.button("🤖 Quick Ask FinPilot AI", use_container_width=True):
        st.session_state["nav"] = "AI Assistant"
        st.rerun()

    # Product Walkthrough Tour Trigger
    if st.button("🎬 Watch App Tour (35s)", use_container_width=True):
        st.session_state["show_app_tour"] = True
        st.rerun()

    st.markdown("""
        <div style="font-size: 0.72rem; color: #64748b; line-height: 1.4; margin-top: 10px;">
            🛡️ <b>Virtual Paper Trading</b><br>
            All funds are 100% simulated.<br>
            Zero real-money financial risk.
        </div>
    """, unsafe_allow_html=True)

# Render App Tour Modal if active
if st.session_state.get("show_app_tour"):
    render_app_tour_modal()

# Render Selected View
PAGES[selected_page]["func"]()
