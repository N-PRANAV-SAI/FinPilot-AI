"""Authentication & 5-Step User Onboarding Component for FinPilot AI."""
import streamlit as st
from database.db import get_session
from backend.services.auth_service import (
    register_user, authenticate_user, save_onboarding_preferences
)
from database.models import User, VirtualAccount


def render_auth_modal():
    """Render high-end authentication & multi-step onboarding modal."""
    if "user" in st.session_state and st.session_state["user"]:
        return st.session_state["user"]

    st.markdown("""
        <div style="text-align: center; margin-bottom: 2rem;">
            <div style="font-size: 3rem;">🛫</div>
            <h1 style="font-size: 2.2rem; font-weight: 800; background: linear-gradient(135deg, #38bdf8, #818cf8); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 0.25rem;">
                FinPilot AI
            </h1>
            <p style="color: #94a3b8; font-size: 1.05rem;">
                Global Financial Intelligence, Virtual Paper Trading & AI Mentorship
            </p>
        </div>
    """, unsafe_allow_html=True)

    tab_login, tab_register = st.tabs(["🔑 Log In", "✨ Create Free Account"])

    with tab_login:
        with st.form("login_form"):
            st.markdown("### Welcome Back")
            email = st.text_input("Email Address", placeholder="e.g. investor@university.edu")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Sign In to FinPilot AI", use_container_width=True)

            if submit:
                if not email or not password:
                    st.error("Please enter both email and password.")
                else:
                    db = next(get_session())
                    try:
                        res = authenticate_user(email, password, db)
                        if res.get("success"):
                            st.session_state["user"] = res["user"]
                            st.success(f"Welcome back, {res['user']['name']}!")
                            st.rerun()
                        else:
                            st.error(res.get("error", "Login failed."))
                    finally:
                        db.close()

        # Demo fast-access
        st.markdown("<p style='text-align:center; color:#64748b; font-size:0.85rem; margin-top:10px;'>Need immediate access for evaluation?</p>", unsafe_allow_html=True)
        if st.button("🚀 Fast-Demo Login (Instant Guest Account)", use_container_width=True):
            db = next(get_session())
            try:
                # Ensure demo user exists
                demo_email = "demo@finpilot.ai"
                res = authenticate_user(demo_email, "Demo12345!", db)
                if not res.get("success"):
                    reg = register_user("Guest Trader", demo_email, "Demo12345!", db)
                    if reg.get("success"):
                        save_onboarding_preferences(
                            user_id=reg["user"]["user_id"],
                            experience_level="Beginner",
                            learning_goals=["Learn how the stock market works", "Practise investing"],
                            risk_comfort="Moderate",
                            preferred_currency="INR",
                            practice_balance=100000.0,
                            trading_mode="Beginner learning mode",
                            db=db
                        )
                        st.session_state["user"] = reg["user"]
                    else:
                        st.session_state["user"] = {"user_id": 1, "name": "Guest Investor", "experience_level": "Beginner", "preferred_currency": "INR", "onboarding_completed": True}
                else:
                    st.session_state["user"] = res["user"]
                st.rerun()
            finally:
                db.close()

    with tab_register:
        with st.form("register_form"):
            st.markdown("### Create Your Account")
            name = st.text_input("Full Name", placeholder="e.g. Pranav Sharma")
            reg_email = st.text_input("Email Address", placeholder="e.g. pranav@example.com")
            reg_pass = st.text_input("Create Password", type="password", help="At least 6 characters")
            reg_pass_confirm = st.text_input("Confirm Password", type="password")
            
            reg_submit = st.form_submit_button("Create Account & Start Onboarding", use_container_width=True)

            if reg_submit:
                if not name or not reg_email or not reg_pass:
                    st.error("Please fill in all required fields.")
                elif reg_pass != reg_pass_confirm:
                    st.error("Passwords do not match.")
                elif len(reg_pass) < 6:
                    st.error("Password must be at least 6 characters.")
                else:
                    db = next(get_session())
                    try:
                        res = register_user(name, reg_email, reg_pass, db)
                        if res.get("success"):
                            st.session_state["user"] = res["user"]
                            st.session_state["trigger_onboarding"] = True
                            st.success("Account created successfully! Starting onboarding...")
                            st.rerun()
                        else:
                            st.error(res.get("error", "Registration failed."))
                    finally:
                        db.close()

    return None


def render_onboarding_flow(user: dict):
    """Render interactive 5-step onboarding wizard for newly registered users."""
    st.markdown("""
        <div style="background: linear-gradient(135deg, rgba(30, 41, 59, 0.8), rgba(15, 23, 42, 0.9)); border: 1px solid #334155; border-radius: 16px; padding: 28px; margin: 2rem auto; max-width: 800px; box-shadow: 0 10px 30px rgba(0,0,0,0.4);">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:1.5rem;">
                <div>
                    <span style="font-size:0.85rem; font-weight:700; color:#38bdf8; text-transform:uppercase; letter-spacing:1px;">Onboarding Wizard</span>
                    <h2 style="margin:4px 0 0; font-size:1.6rem; color:#f8fafc;">Personalize Your FinPilot AI Experience</h2>
                </div>
                <div style="font-size:2rem;">🎓</div>
            </div>
            <p style="color:#94a3b8; font-size:0.95rem; line-height:1.5; margin-bottom:1.5rem;">
                Answer these 5 quick questions so FinPilot AI can tailor explanations, risk warnings, and initial practice funds to your exact background.
            </p>
        </div>
    """, unsafe_allow_html=True)

    with st.form("onboarding_form"):
        # Step 1: Experience
        st.markdown("#### Step 1: How experienced are you with investing?")
        exp = st.radio(
            "Select experience level:",
            options=[
                "Beginner — I am completely new",
                "Intermediate — I understand the basics",
                "Advanced — I have investment experience"
            ],
            index=0
        )
        exp_clean = "Beginner" if "Beginner" in exp else ("Intermediate" if "Intermediate" in exp else "Advanced")

        st.markdown("---")

        # Step 2: Learning Goals
        st.markdown("#### Step 2: What would you like to achieve? *(Select all that apply)*")
        g1 = st.checkbox("Learn how the stock market works", value=True)
        g2 = st.checkbox("Practise investing with virtual money", value=True)
        g3 = st.checkbox("Understand global companies across US, India, Europe & Asia", value=True)
        g4 = st.checkbox("Build a diversified investment portfolio", value=True)
        g5 = st.checkbox("Learn quantitative & machine learning financial analysis")
        g6 = st.checkbox("Improve investment decision-making")

        selected_goals = []
        if g1: selected_goals.append("Learn how the stock market works")
        if g2: selected_goals.append("Practise investing")
        if g3: selected_goals.append("Understand global companies")
        if g4: selected_goals.append("Build a diversified portfolio")
        if g5: selected_goals.append("Learn financial analysis")
        if g6: selected_goals.append("Improve investment decision-making")

        st.markdown("---")

        # Step 3: Risk Comfort
        st.markdown("#### Step 3: How comfortable are you with investment risk?")
        st.caption("Beginner Guide: High risk can lead to bigger short-term swings; low risk focuses on capital preservation.")
        risk = st.select_slider(
            "Select your risk comfort level:",
            options=["Low", "Moderate", "High", "I am not sure yet"],
            value="Moderate"
        )

        st.markdown("---")

        # Step 4: Virtual Practice Balance & Currency
        st.markdown("#### Step 4: How much virtual money would you like to start practising with?")
        st.caption("🛡️ **PAPER TRADING**: These funds are 100% simulated fake money for educational testing.")
        
        c1, c2 = st.columns([1, 1])
        with c1:
            currency = st.selectbox(
                "Select Virtual Account Currency:",
                options=["INR (₹)", "USD ($)", "EUR (€)", "GBP (£)"],
                index=0
            )
            curr_code = currency.split()[0]
        with c2:
            balance_presets = {
                "₹10,000 / $1,000": 10000.0 if curr_code == "INR" else 1000.0,
                "₹50,000 / $5,000": 50000.0 if curr_code == "INR" else 5000.0,
                "₹1,00,000 / $10,000 (Recommended)": 100000.0 if curr_code == "INR" else 10000.0,
                "₹5,00,000 / $50,000": 500000.0 if curr_code == "INR" else 50000.0,
                "₹10,00,000 / $100,000": 1000000.0 if curr_code == "INR" else 100000.0,
            }
            chosen_preset = st.selectbox("Choose Starting Practice Capital:", list(balance_presets.keys()), index=2)
            balance = balance_presets[chosen_preset]

        st.markdown("---")

        # Step 5: Trading Mode
        st.markdown("#### Step 5: Which platform mode do you prefer?")
        mode = st.radio(
            "Select default UI mode:",
            options=[
                "Beginner learning mode (Simplified terms, educational tips, analogy guidance)",
                "Normal investing mode (Clean portfolio tracking and real-time execution)",
                "Advanced analysis mode (In-depth ML metrics, SHAP contributions, technical oscillators)"
            ],
            index=0
        )
        mode_clean = "Beginner learning mode" if "Beginner" in mode else ("Advanced analysis mode" if "Advanced" in mode else "Normal investing mode")

        submitted = st.form_submit_button("Complete Onboarding & Enter FinPilot AI 🚀", use_container_width=True)

        if submitted:
            db = next(get_session())
            try:
                res = save_onboarding_preferences(
                    user_id=user["user_id"],
                    experience_level=exp_clean,
                    learning_goals=selected_goals,
                    risk_comfort=risk,
                    preferred_currency=curr_code,
                    practice_balance=balance,
                    trading_mode=mode_clean,
                    db=db
                )
                if res.get("success"):
                    st.session_state["user"]["experience_level"] = exp_clean
                    st.session_state["user"]["preferred_currency"] = curr_code
                    st.session_state["user"]["preferred_mode"] = mode_clean
                    st.session_state["user"]["onboarding_completed"] = True
                    st.session_state["trigger_onboarding"] = False
                    st.success("Preferences saved! Welcome to FinPilot AI.")
                    st.rerun()
                else:
                    st.error("Failed to save preferences.")
            finally:
                db.close()
