"""Beginner Financial Education & Interactive Learning Center Interface for FinPilot AI."""
import streamlit as st
from backend.education.learning_center import LearningCenterService, LESSONS_DATABASE
from database.db import get_session
from database.models import LearningProgress


def render_learning_page():
    """Render structured financial lessons, quizzes, and financial glossary."""
    user = st.session_state.get("user", {})
    user_id = user.get("user_id", 1)

    st.markdown("""
        <div style="margin-bottom: 1.5rem;">
            <div style="font-size: 0.85rem; font-weight: 700; color: #38bdf8; text-transform: uppercase; letter-spacing: 1px;">
                Financial Literacy & Education
            </div>
            <h1 style="margin: 0.2rem 0; font-size: 2.2rem; font-weight: 800; color: #f8fafc;">
                Beginner Learning Centre
            </h1>
            <p style="color: #94a3b8; font-size: 0.95rem;">
                Master core financial concepts, test your understanding with interactive quizzes, and build confidence before paper trading.
            </p>
        </div>
    """, unsafe_allow_html=True)

    db = next(get_session())
    try:
        lessons = LearningCenterService.get_all_lessons(user_id, db)
    finally:
        db.close()

    completed_count = sum(1 for l in lessons if l.get("completed"))
    progress_pct = (completed_count / len(lessons)) * 100 if lessons else 0.0

    # Learning Progress Bar
    p_col1, p_col2 = st.columns([3, 1])
    with p_col1:
        st.progress(progress_pct / 100.0)
    with p_col2:
        st.markdown(f"**{completed_count} of {len(lessons)} Lessons Completed** ({progress_pct:.0f}%)")

    st.markdown("<br>", unsafe_allow_html=True)

    tab_lessons, tab_glossary = st.tabs(["📚 Interactive Lessons & Quizzes", "📖 Financial Glossary"])

    with tab_lessons:
        # Lesson Selector
        lesson_titles = [f"{'✅ ' if l.get('completed') else '📖 '}{l['title']} ({l['category']} • {l['read_time']})" for l in lessons]
        selected_idx = st.selectbox("Select a Lesson to Study:", range(len(lesson_titles)), format_func=lambda i: lesson_titles[i])
        current_lesson = lessons[selected_idx]

        # Lesson Display Card
        st.markdown(f"""
            <div style="background: #0f172a; border: 1px solid #1e293b; border-radius: 12px; padding: 24px; margin-bottom: 1.5rem;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                    <span style="background: #1e293b; border: 1px solid #334155; padding: 4px 10px; border-radius: 20px; font-size: 0.8rem; color: #38bdf8; font-weight: 600;">
                        {current_lesson['category']}
                    </span>
                    <span style="color: #64748b; font-size: 0.85rem;">⏱️ {current_lesson['read_time']} read</span>
                </div>
                <h2 style="color: #f8fafc; font-size: 1.6rem; margin-top: 0;">{current_lesson['title']}</h2>
                <div style="color: #94a3b8; font-size: 1.05rem; line-height: 1.6; margin-bottom: 1.5rem;">
                    <em>{current_lesson['summary']}</em>
                </div>
            </div>
        """, unsafe_allow_html=True)

        st.markdown(current_lesson["content"])

        st.markdown("---")

        # Interactive Quiz Section
        if "quiz" in current_lesson:
            quiz = current_lesson["quiz"]
            st.markdown(f"### 📝 Quick Knowledge Check: {current_lesson['title']}")
            st.markdown(f"**Question:** {quiz['question']}")

            user_choice = st.radio(
                "Select your answer:",
                options=range(len(quiz["options"])),
                format_func=lambda i: quiz["options"][i],
                key=f"quiz_radio_{current_lesson['id']}"
            )

            if st.button("Submit Answer", key=f"btn_quiz_{current_lesson['id']}", type="primary"):
                db = next(get_session())
                try:
                    res = LearningCenterService.submit_quiz_answer(
                        user_id=user_id,
                        lesson_id=current_lesson["id"],
                        selected_option_index=user_choice,
                        db=db
                    )
                    if res.get("is_correct"):
                        st.success(f"🎉 **Correct!** {res.get('explanation')}")
                        st.balloons()
                        st.rerun()
                    else:
                        st.error(f"❌ **Incorrect.** {res.get('explanation')}")
                finally:
                    db.close()

    with tab_glossary:
        st.markdown("### 📖 Instant Financial Glossary")
        st.caption("Search or browse definitions of key trading and financial analysis terms.")

        search_term = st.text_input("🔍 Search glossary (e.g. RSI, P/E, Dividend, Ticker):", "").lower().strip()

        glossary_items = [
            ("Bull Market", "A prolonged financial market condition where asset prices are steadily rising and investor confidence is strong."),
            ("Bear Market", "A market condition where asset prices drop by 20% or more from recent peaks, accompanied by widespread investor pessimism."),
            ("Market Order", "An order executed immediately at the prevailing current market price, prioritizing speed over exact price control."),
            ("Limit Order", "An order to buy or sell an asset at a specified price or better, ensuring price discipline at the expense of guaranteed execution."),
            ("P/E Ratio (Price-to-Earnings)", "Stock price divided by earnings per share. Measures how many dollars/rupees investors pay per unit of current earnings."),
            ("RSI (Relative Strength Index)", "A momentum oscillator from 0 to 100 measuring recent price changes. Above 70 is overbought, below 30 is oversold."),
            ("MACD", "A trend-following momentum indicator displaying the relationship between two moving averages of a security's price."),
            ("SHAP (Explainable AI)", "Shapley Additive exPlanations — a game-theoretic approach that explains how each individual feature contributed to an AI prediction."),
            ("FinBERT", "A financial domain-specific BERT language model trained to classify tone and sentiment in corporate earnings reports and market news."),
            ("Paper Trading", "Simulated trading using virtual fake capital with live real-time market data to practice strategy without financial risk."),
            ("Diversification", "Spreading investment capital across diverse companies, industries, and geographies to reduce portfolio concentration risk.")
        ]

        filtered = [item for item in glossary_items if not search_term or search_term in item[0].lower() or search_term in item[1].lower()]

        for term, definition in filtered:
            with st.expander(f"📌 {term}"):
                st.write(definition)
