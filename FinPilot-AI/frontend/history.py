"""Analysis History page for FinPilot AI."""
import streamlit as st
import pandas as pd
from database.db import SessionLocal
from database.models import AnalysisHistory, Prediction, ModelMetrics


def render_history():
    """Render historical persisted analyses, predictions, and model metrics from SQLite."""
    st.markdown("## 📜 Analysis History & Audit Trail")
    st.caption("All completed financial analyses, model predictions, and AI explanations persisted in SQLite.")

    db = SessionLocal()
    try:
        # Fetch analyses
        history_records = (
            db.query(AnalysisHistory)
            .order_by(AnalysisHistory.analysis_date.desc())
            .limit(100)
            .all()
        )

        if not history_records:
            st.info("ℹ️ No saved analyses found in the database. Run an analysis from the **Dashboard** to record entries.")
            return

        # Summary Metrics
        total_runs = len(history_records)
        unique_tickers = len(set(h.ticker for h in history_records))
        latest_date = history_records[0].analysis_date.strftime("%Y-%m-%d %H:%M UTC") if history_records[0].analysis_date else "N/A"

        c1, c2, c3 = st.columns(3)
        c1.metric("Total Analysis Runs", total_runs)
        c2.metric("Unique Assets Covered", unique_tickers)
        c3.metric("Most Recent Analysis", latest_date)

        st.markdown("---")

        # Search / Filter
        search_ticker = st.text_input("Filter by Ticker Symbol:", value="").strip().upper()
        if search_ticker:
            history_records = [h for h in history_records if search_ticker in (h.ticker or "")]

        st.markdown(f"### Saved Analysis Records ({len(history_records)})")

        for idx, item in enumerate(history_records):
            date_str = item.analysis_date.strftime("%Y-%m-%d %H:%M") if item.analysis_date else "N/A"
            t = item.ticker or "Unknown"
            comp = item.company_name or t
            cntry = getattr(item, "country", "Global") or "Global"
            exc = getattr(item, "exchange", "N/A") or "N/A"
            curr = getattr(item, "currency", "USD") or "USD"
            from backend.data.global_exchanges import get_exchange_info
            flag = get_exchange_info(exc or t).flag

            with st.expander(f"📁 {flag} **{t}** — {comp} ({exc}, {cntry} | {curr}) ({date_str}) | {item.prediction_summary}", expanded=(idx == 0)):
                c_p, c_s, c_m = st.columns(3)
                with c_p:
                    st.write("**Directional Prediction:**")
                    st.write(item.prediction_summary or "N/A")
                with c_s:
                    st.write("**News Sentiment:**")
                    st.write(item.sentiment_summary or "N/A")
                with c_m:
                    st.write(f"**Architecture & Market ({curr}):**")
                    st.write(f"`{item.selected_model or 'Default'}` • {exc}")

                st.markdown("##### 📄 AI Financial Research Report")
                if item.llm_explanation and item.llm_explanation != "Not generated yet.":
                    st.markdown(item.llm_explanation)
                else:
                    st.caption("No LLM explanation was generated for this session.")

        # Database Maintenance
        with st.expander("⚙️ Database Diagnostics & Management", expanded=False):
            pred_count = db.query(Prediction).count()
            metric_count = db.query(ModelMetrics).count()
            st.write(f"• **Stored Predictions:** `{pred_count}`")
            st.write(f"• **Stored Model Metrics:** `{metric_count}`")
            if st.button("🗑️ Clear All Analysis History", type="secondary"):
                db.query(AnalysisHistory).delete()
                db.commit()
                st.success("Analysis history cleared successfully.")
                st.rerun()

    finally:
        db.close()
