"""Dedicated AI Financial Assistant Interface for FinPilot AI."""
import streamlit as st
from backend.assistant.ai_assistant import FinPilotAIAssistant
from backend.trading.paper_engine import PaperTradingEngine
from database.db import get_session


def render_ai_assistant_page():
    """Render intelligent, context-aware financial assistant with beginner & advanced modes."""
    user = st.session_state.get("user", {})
    user_id = user.get("user_id", 1)

    st.markdown("""
        <div style="margin-bottom: 1.5rem;">
            <div style="font-size: 0.85rem; font-weight: 700; color: #818cf8; text-transform: uppercase; letter-spacing: 1px;">
                Intelligent Financial Copilot
            </div>
            <h1 style="margin: 0.2rem 0; font-size: 2.2rem; font-weight: 800; color: #f8fafc;">
                FinPilot AI Assistant
            </h1>
            <p style="color: #94a3b8; font-size: 0.95rem;">
                Your 24/7 financial mentor, quantitative analyst, and guided paper-trading advisor.
            </p>
        </div>
    """, unsafe_allow_html=True)

    # Context Header: Current Mode & Selected Asset
    top_c1, top_c2 = st.columns([1.5, 1])
    with top_c1:
        current_exp = user.get("experience_level", "Beginner")
        mode_choice = st.radio(
            "Assistant Persona Mode:",
            ["Beginner Mode (Simple analogies, risk warnings, glossary definitions)", "Advanced Mode (Quantitative metrics, SHAP contributions, technical oscillators)"],
            index=0 if "Beginner" in current_exp else 1,
            horizontal=True
        )
        is_beginner = "Beginner" in mode_choice
        user["experience_level"] = "Beginner" if is_beginner else "Advanced"

    with top_c2:
        active_analysis = st.session_state.get("active_analysis")
        if active_analysis:
            st.info(f"🎯 **Active Asset Context**: {active_analysis.get('company_name')} (`{active_analysis.get('ticker')}`)")
        else:
            st.caption("💡 *Tip: Analyze a stock on the Dashboard or Search page to give the Assistant live asset context!*")

    # Fetch user portfolio context
    db = next(get_session())
    try:
        portfolio_ctx = PaperTradingEngine.get_user_account_summary(user_id, db)
    finally:
        db.close()

    # Chat history state
    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = [
            {
                "role": "assistant",
                "content": f"👋 Hello **{user.get('name', 'Investor')}**! I am your FinPilot AI Assistant. I can help you decode company balance sheets, explain complex indicators like RSI and P/E, or guide you step-by-step through simulated practice trades. What would you like to explore today?"
            }
        ]

    # Quick prompt chip shortcuts
    st.markdown("##### ⚡ Quick Questions:")
    quick_col1, quick_col2, quick_col3, quick_col4 = st.columns(4)
    quick_prompt = None
    with quick_col1:
        if st.button("📚 Explain P/E & RSI", use_container_width=True):
            quick_prompt = "What does P/E ratio and RSI mean? Give an easy beginner example."
    with quick_col2:
        if st.button("🛡️ Diversification Risk", use_container_width=True):
            quick_prompt = "Why is portfolio diversification important, and am I too concentrated?"
    with quick_col3:
        if st.button("🎯 Practice Investment", use_container_width=True):
            t = active_analysis.get("ticker", "Apple") if active_analysis else "NVIDIA"
            quick_prompt = f"Help me practise investing in {t} using my virtual funds. What factors should I check first?"
    with quick_col4:
        if st.button("🤖 Explain ML & SHAP", use_container_width=True):
            quick_prompt = "How does the Machine Learning model predict stock direction, and what is SHAP?"

    # Display chat messages
    for msg in st.session_state["chat_history"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Input handling
    user_input = st.chat_input("Ask FinPilot AI Assistant anything about stocks, portfolios, or indicators...")
    prompt_to_send = quick_prompt or user_input

    if prompt_to_send:
        # Append user message
        st.session_state["chat_history"].append({"role": "user", "content": prompt_to_send})
        with st.chat_message("user"):
            st.markdown(prompt_to_send)

        # Generate response
        assistant_service = FinPilotAIAssistant()
        with st.chat_message("assistant"):
            with st.spinner("FinPilot AI is synthesizing financial analysis..."):
                reply = assistant_service.generate_response(
                    user_message=prompt_to_send,
                    user_profile=user,
                    portfolio_context=portfolio_ctx,
                    company_context=active_analysis
                )
                st.markdown(reply)
                st.session_state["chat_history"].append({"role": "assistant", "content": reply})
