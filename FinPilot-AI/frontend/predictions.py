"""Machine Learning Predictions page for FinPilot AI."""
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np


def render_predictions():
    """Render ML predictions, validation vs held-out test evaluation, and confusion matrix."""
    st.markdown("## 🤖 Machine Learning 5-Day Directional Prediction")

    analysis = st.session_state.get("analysis")
    if not analysis:
        st.info("💡 Please run an analysis from the **Dashboard** first.")
        return

    pred = analysis.get("prediction", {})
    training = analysis.get("training", {})
    ticker = analysis["ticker"]
    results = training.get("results", {})
    selected_model_name = training.get("selected_model", "Selected Model")

    # Prediction Summary Banner
    direction = pred.get("direction", "N/A")
    pos_prob = pred.get("positive_probability", 0.5)
    neg_prob = pred.get("negative_probability", 0.5)
    is_positive = pred.get("predicted_class") == 1

    badge_color = "#10b981" if is_positive else "#f43f5e"
    badge_bg = "rgba(16, 185, 129, 0.15)" if is_positive else "rgba(244, 63, 94, 0.15)"
    border_color = "rgba(16, 185, 129, 0.4)" if is_positive else "rgba(244, 63, 94, 0.4)"

    comp_name = analysis.get("company_name", ticker)
    country = analysis.get("country", "Global")
    exchange = analysis.get("exchange", "Exchange")
    flag = analysis.get("flag", "🌐")

    st.markdown(f"""
        <div style="background-color: {badge_bg}; border: 2px solid {border_color}; border-radius: 12px; padding: 24px; margin-bottom: 1.5rem;">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
                <div>
                    <span style="text-transform: uppercase; letter-spacing: 0.08em; font-size: 0.85rem; color: #94a3b8; font-weight: 600;">
                        Target: Next 5 {exchange} Trading Sessions Forward Direction
                    </span>
                    <h1 style="margin: 6px 0; color: {badge_color}; font-size: 2.2rem; font-weight: 800;">
                        {direction} Outlook — {flag} {comp_name} ({ticker})
                    </h1>
                    <span style="color: #cbd5e1; font-size: 0.95rem;">
                        Exchange: <b>{exchange} ({country})</b> | 
                        Selected Model: <b>{selected_model_name}</b> | 
                        Horizon: <b>5 Exchange Trading Sessions</b> | 
                        Observation Date: <b>{pred.get('last_market_date', 'Latest')}</b>
                    </span>
                </div>
                <div style="text-align: right; min-width: 220px;">
                    <div style="font-size: 0.85rem; color: #94a3b8; margin-bottom: 4px;">Class Probability Distribution</div>
                    <div style="font-size: 1.6rem; font-weight: 800; color: {badge_color};">
                        {pos_prob:.1%} <span style="font-size: 0.9rem; font-weight: 400; color: #94a3b8;">Positive</span>
                    </div>
                    <div style="font-size: 1.1rem; font-weight: 600; color: #94a3b8;">
                        {neg_prob:.1%} <span style="font-size: 0.8rem; font-weight: 400; color: #64748b;">Negative/Flat</span>
                    </div>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Class Probability Gauge & Bars
    c1, c2 = st.columns([1, 1])
    with c1:
        st.markdown("#### Probability Distribution")
        st.write(f"**Class 1 (Positive Return):** `{pos_prob:.1%}`")
        st.progress(float(pos_prob))
        st.write(f"**Class 0 (Negative or Flat Return):** `{neg_prob:.1%}`")
        st.progress(float(neg_prob))

    with c2:
        st.markdown("#### Chronological Split Summary")
        st.write(f"• **Training Set:** `{training.get('train_size', 0)} rows` (up to {training.get('last_train_date', 'N/A')})")
        st.write(f"• **Validation Set:** `{training.get('val_size', 0)} rows` (up to {training.get('last_val_date', 'N/A')})")
        st.write(f"• **Held-Out Test Set:** `{training.get('test_size', 0)} rows` ({training.get('test_start_date', 'N/A')} to {training.get('test_end_date', 'N/A')})")
        st.caption("🔒 **Strict Chronology:** No data shuffling or random K-fold splits were applied.")

    st.markdown("---")

    # Candidate Model Evaluation Comparison Table
    st.markdown("### 🏆 Candidate Model Performance Comparison")
    st.caption(
        "Candidate models were trained on historical training rows and compared on the **chronological validation set**. "
        "The best model was chosen via validation ROC-AUC, refit on train+validation, and evaluated **once** on the untouched test set."
    )

    rows = []
    for name, m_dict in results.items():
        val = m_dict.get("validation", {})
        test = m_dict.get("test", {})
        is_selected = (name == selected_model_name)
        rows.append({
            "Model": f"★ {name} (Selected)" if is_selected else name,
            "Val ROC-AUC": f"{val.get('roc_auc', 0):.4f}" if np.isfinite(val.get("roc_auc", float("nan"))) else "N/A",
            "Val Accuracy": f"{val.get('accuracy', 0):.2%}" if "accuracy" in val else "N/A",
            "Val F1-Score": f"{val.get('f1', 0):.4f}" if "f1" in val else "N/A",
            "Val Precision": f"{val.get('precision', 0):.4f}" if "precision" in val else "N/A",
            "Val Recall": f"{val.get('recall', 0):.4f}" if "recall" in val else "N/A",
            "Test ROC-AUC": f"{test.get('roc_auc', 0):.4f}" if "roc_auc" in test and np.isfinite(test.get("roc_auc", float("nan"))) else "-",
            "Test Accuracy": f"{test.get('accuracy', 0):.2%}" if "accuracy" in test else "-",
            "Test F1-Score": f"{test.get('f1', 0):.4f}" if "f1" in test else "-",
        })

    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    # Confusion Matrix Visualization for Selected Model
    sel_metrics = results.get(selected_model_name, {})
    test_metrics = sel_metrics.get("test", {})
    cm = test_metrics.get("confusion_matrix")

    if cm and len(cm) == 2:
        st.markdown(f"### 🎯 Held-Out Test Confusion Matrix ({selected_model_name})")
        cm_arr = np.array(cm)
        tn, fp = cm_arr[0, 0], cm_arr[0, 1]
        fn, tp = cm_arr[1, 0], cm_arr[1, 1]

        fig = go.Figure(data=go.Heatmap(
            z=cm_arr,
            x=["Predicted Class 0 (Down/Flat)", "Predicted Class 1 (Up)"],
            y=["Actual Class 0 (Down/Flat)", "Actual Class 1 (Up)"],
            colorscale=[[0, "#1e293b"], [0.5, "#1d4ed8"], [1, "#38bdf8"]],
            text=[[f"TN: {tn}", f"FP: {fp}"], [f"FN: {fn}", f"TP: {tp}"]],
            texttemplate="%{text}",
            textfont=dict(size=16, color="white"),
        ))
        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            height=320,
            margin=dict(l=0, r=0, t=10, b=0),
        )
        st.plotly_chart(fig, use_container_width=True)

    st.info(
        "💡 **Methodological Integrity Notice:** Predictive models for short-term asset prices operate in low signal-to-noise "
        "regimes. A directional probability of 55%–65% represents a meaningful statistical edge in quantitative finance, "
        "not a certainty. Never risk capital without proper stop-loss and risk management."
    )
