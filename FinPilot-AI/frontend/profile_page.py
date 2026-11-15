"""User Profile and Platform Settings Interface for FinPilot AI."""
import streamlit as st
from database.db import get_session
from database.models import User, VirtualAccount
from backend.trading.paper_engine import PaperTradingEngine
from config.settings import settings


def render_profile_page():
    """Render user profile, learning preferences, and virtual account configuration."""
    user = st.session_state.get("user", {})
    user_id = user.get("user_id", 1)

    st.markdown("""
        <div style="margin-bottom: 1.5rem;">
            <div style="font-size: 0.85rem; font-weight: 700; color: #38bdf8; text-transform: uppercase; letter-spacing: 1px;">
                User Account & Preferences
            </div>
            <h1 style="margin: 0.2rem 0; font-size: 2.2rem; font-weight: 800; color: #f8fafc;">
                Account Profile & Settings
            </h1>
            <p style="color: #94a3b8; font-size: 0.95rem;">
                Manage your virtual trading funds, experience level, account currency, and system credentials.
            </p>
        </div>
    """, unsafe_allow_html=True)

    db = next(get_session())
    try:
        user_record = db.query(User).filter(User.user_id == user_id).first()
        portfolio_summary = PaperTradingEngine.get_user_account_summary(user_id, db)
    finally:
        db.close()

    acc_curr = portfolio_summary.get("account_currency", "INR")
    avail_cash = portfolio_summary.get("available_cash", 100000.0)

    # 1. USER PROFILE CARD
    col_profile, col_wallet = st.columns(2)

    with col_profile:
        st.markdown(f"""
            <div style="background: #0f172a; border: 1px solid #1e293b; border-radius: 12px; padding: 22px; margin-bottom: 1.5rem;">
                <h3 style="margin-top: 0; color: #f8fafc;">👤 Personal Information</h3>
                <div style="margin-bottom: 8px; color: #94a3b8;">
                    Full Name: <b style="color: #f8fafc;">{user.get('name', 'Investor')}</b>
                </div>
                <div style="margin-bottom: 8px; color: #94a3b8;">
                    Email: <b style="color: #f8fafc;">{user.get('email', 'investor@finpilot.ai')}</b>
                </div>
                <div style="margin-bottom: 8px; color: #94a3b8;">
                    Current Level: <b style="color: #38bdf8;">{user.get('experience_level', 'Beginner')}</b>
                </div>
                <div style="color: #94a3b8;">
                    Preferred Mode: <b style="color: #4ade80;">{user.get('preferred_mode', 'Beginner learning mode')}</b>
                </div>
            </div>
        """, unsafe_allow_html=True)

    with col_wallet:
        st.markdown(f"""
            <div style="background: #0f172a; border: 1px solid #1e293b; border-radius: 12px; padding: 22px; margin-bottom: 1.5rem;">
                <h3 style="margin-top: 0; color: #f8fafc;">💰 Virtual Practice Capital</h3>
                <div style="margin-bottom: 8px; color: #94a3b8;">
                    Available Cash: <b style="color: #38bdf8; font-size: 1.2rem;">{acc_curr} {avail_cash:,.2f}</b>
                </div>
                <div style="margin-bottom: 8px; color: #94a3b8;">
                    Account Currency: <b style="color: #f8fafc;">{acc_curr}</b>
                </div>
                <div style="color: #94a3b8;">
                    Mode: <b style="color: #f59e0b;">🛡️ 100% Simulated Paper Trading</b>
                </div>
            </div>
        """, unsafe_allow_html=True)

    tab_funds, tab_prefs, tab_system = st.tabs([
        "💵 Virtual Funds Management",
        "🎓 Learning & Trading Preferences",
        "🔌 API Providers & System Health"
    ])

    with tab_funds:
        st.markdown("### Top-Up or Reset Virtual Balance")
        f_col1, f_col2 = st.columns(2)

        with f_col1:
            st.markdown("#### ➕ Add Virtual Funds")
            st.caption("Inject additional practice capital into your simulation account.")
            add_amt = st.number_input("Amount to Add (Virtual):", min_value=1000.0, value=50000.0, step=10000.0, key="prof_add_amt")
            if st.button("Add Fake Practice Money", use_container_width=True, type="primary"):
                db = next(get_session())
                try:
                    res = PaperTradingEngine.add_virtual_funds(user_id, add_amt, db)
                    if res.get("success"):
                        st.success(res.get("message"))
                        st.rerun()
                finally:
                    db.close()

        with f_col2:
            st.markdown("#### 🔄 Reset Simulation Account")
            st.caption("Clears all existing positions and resets your balance.")
            new_reset_bal = st.number_input("Reset Balance to:", min_value=10000.0, value=100000.0, step=10000.0, key="prof_reset_amt")
            if st.button("Confirm Complete Account Reset", use_container_width=True):
                db = next(get_session())
                try:
                    res = PaperTradingEngine.reset_virtual_account(user_id, new_reset_bal, db)
                    if res.get("success"):
                        st.success(res.get("message"))
                        st.rerun()
                finally:
                    db.close()

    with tab_prefs:
        st.markdown("### Update Experience & Navigation Mode")
        with st.form("pref_update_form"):
            new_exp = st.selectbox(
                "Experience Level:",
                ["Beginner — I am completely new", "Intermediate — I understand the basics", "Advanced — I have investment experience"],
                index=0 if user.get("experience_level") == "Beginner" else 1
            )
            new_curr = st.selectbox(
                "Account Currency:",
                ["INR", "USD", "EUR", "GBP"],
                index=0 if acc_curr == "INR" else 1
            )
            save_pref_btn = st.form_submit_button("Save Preferences", use_container_width=True)

            if save_pref_btn:
                clean_exp = "Beginner" if "Beginner" in new_exp else ("Intermediate" if "Intermediate" in new_exp else "Advanced")
                db = next(get_session())
                try:
                    u = db.query(User).filter(User.user_id == user_id).first()
                    if u:
                        u.experience_level = clean_exp
                        u.preferred_currency = new_curr
                        v = db.query(VirtualAccount).filter(VirtualAccount.user_id == user_id).first()
                        if v:
                            v.account_currency = new_curr
                        db.commit()
                        st.session_state["user"]["experience_level"] = clean_exp
                        st.session_state["user"]["preferred_currency"] = new_curr
                        st.success("Preferences updated successfully!")
                        st.rerun()
                finally:
                    db.close()

    with tab_system:
        st.markdown("### Configured Providers & System Diagnostics")
        st.markdown(f"""
            - **Google Gemini API**: `{'🟢 Connected (' + settings.gemini_model + ')' if settings.gemini_api_key else '⚠️ Offline (Fallback active)'}`
            - **Finnhub News API**: `{'🟢 Connected' if settings.finnhub_api_key else '⚠️ Offline (Fallback active)'}`
            - **Global Market Provider**: `🟢 Yahoo Finance & EODHD Multi-Exchange Provider Active`
            - **Vector Store**: `🟢 ChromaDB Active (MiniLM-L6-v2 Embeddings)`
            - **Database**: `🟢 SQLite Persistent Storage (finpilot.db)`
            - **FastAPI Backend Server**: `🟢 Running on http://127.0.0.1:8000`
        """)

    st.markdown("<hr style='border-color: #1e293b; margin: 30px 0;'>", unsafe_allow_html=True)
    if st.button("🚪 Sign Out of FinPilot AI", use_container_width=True):
        st.session_state["user"] = None
        st.session_state["analysis"] = None
        st.rerun()
