"""Model Comparison page for FinPilot AI."""
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np


def render_comparison():
    """Render comprehensive comparison across algorithms and Quantitative vs Hybrid paradigms."""
    st.markdown("## ⚖️ Quantitative vs Hybrid Model Comparison")
    st.caption("Empirical evaluation of algorithmic architectures and the incremental predictive value of FinBERT sentiment.")

    analysis = st.session_state.get("analysis")
    if not analysis:
        st.info("💡 Please run an analysis from the **Dashboard** first.")
        return

    quant_training = analysis.get("training", {})
    hybrid_training = analysis.get("hybrid_training")
    ticker = analysis["ticker"]
    comp_name = analysis.get("company_name", ticker)
    flag = analysis.get("flag", "🌐")
    exchange = analysis.get("exchange", "Exchange")
    country = analysis.get("country", "Global")

    st.markdown(f"### Evaluating Models for {flag} {comp_name} ({ticker}) — {exchange}, {country}")
    st.caption(
        "Comparison of baseline architectures using strictly technical indicators (Moving averages, RSI, MACD, Volatility, Momentum). "
        "Evaluated on identical chronological splits without cross-currency nominal distortions."
    )

    quant_results = quant_training.get("results", {})
    if quant_results:
        q_rows = []
        metrics_for_chart = []
        for name, m_dict in quant_results.items():
            val = m_dict.get("validation", {})
            test = m_dict.get("test", {})
            q_rows.append({
                "Model Architecture": name,
                "Val ROC-AUC": val.get("roc_auc", float("nan")),
                "Val Accuracy": val.get("accuracy", float("nan")),
                "Val F1-Score": val.get("f1", float("nan")),
                "Val Precision": val.get("precision", float("nan")),
                "Val Recall": val.get("recall", float("nan")),
                "Test ROC-AUC": test.get("roc_auc", float("nan")),
                "Test Accuracy": test.get("accuracy", float("nan")),
                "Test F1-Score": test.get("f1", float("nan")),
            })
            if np.isfinite(val.get("roc_auc", float("nan"))):
                metrics_for_chart.append({
                    "model": name,
                    "roc_auc": val.get("roc_auc"),
                    "accuracy": val.get("accuracy"),
                    "f1": val.get("f1"),
                })

        # Display Formatted Table
        df_display = pd.DataFrame(q_rows)
        st.dataframe(
            df_display.style.format({
                "Val ROC-AUC": "{:.4f}",
                "Val Accuracy": "{:.2%}",
                "Val F1-Score": "{:.4f}",
                "Val Precision": "{:.4f}",
                "Val Recall": "{:.4f}",
                "Test ROC-AUC": "{:.4f}",
                "Test Accuracy": "{:.2%}",
                "Test F1-Score": "{:.4f}",
            }, na_rep="N/A"),
            use_container_width=True,
            hide_index=True,
        )

        # Plotly Bar Chart for Algorithm Comparison
        if metrics_for_chart:
            fig = go.Figure()
            models_list = [m["model"] for m in metrics_for_chart]
            fig.add_trace(go.Bar(
                name="Validation ROC-AUC",
                x=models_list,
                y=[m["roc_auc"] for m in metrics_for_chart],
                marker_color="#38bdf8",
            ))
            fig.add_trace(go.Bar(
                name="Validation Accuracy",
                x=models_list,
                y=[m["accuracy"] for m in metrics_for_chart],
                marker_color="#10b981",
            ))
            fig.add_trace(go.Bar(
                name="Validation F1-Score",
                x=models_list,
                y=[m["f1"] for m in metrics_for_chart],
                marker_color="#a855f7",
            ))
            fig.update_layout(
                barmode="group",
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                height=340,
                margin=dict(l=0, r=0, t=10, b=0),
                yaxis=dict(title="Score", range=[0.4, 1.0], showgrid=True, gridcolor="#1e293b"),
            )
            st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # Section 2: Quantitative vs Hybrid Paradigm Comparison
    st.markdown("### 2. Paradigm Evaluation: Quantitative-Only vs Hybrid (FinBERT Sentiment)")
    st.caption("Research Question: Does the inclusion of FinBERT news sentiment features improve out-of-sample directional prediction?")

    if hybrid_training and hybrid_training.get("results"):
        hybrid_results = hybrid_training.get("results", {})
        selected_algo = quant_training.get("selected_model", "Selected Model")

        q_val = quant_results.get(selected_algo, {}).get("validation", {})
        h_val = hybrid_results.get(selected_algo, {}).get("validation", {})

        q_auc = q_val.get("roc_auc", 0.5)
        h_auc = h_val.get("roc_auc", 0.5)
        delta_auc = h_auc - q_auc

        # Comparison Metrics Row
        col_q, col_h, col_delta = st.columns(3)
        with col_q:
            st.metric(
                label=f"Approach A: Quantitative-Only ({selected_algo})",
                value=f"{q_auc:.4f} ROC-AUC",
                delta=f"Accuracy: {q_val.get('accuracy', 0):.1%}",
            )
        with col_h:
            st.metric(
                label=f"Approach B: Hybrid + FinBERT ({selected_algo})",
                value=f"{h_auc:.4f} ROC-AUC",
                delta=f"Accuracy: {h_val.get('accuracy', 0):.1%}",
            )
        with col_delta:
            st.metric(
                label="Sentiment Incremental Alpha (Δ ROC-AUC)",
                value=f"{delta_auc:+.4f}",
                delta="Improved" if delta_auc > 0 else ("Degraded / Neutral" if delta_auc < 0 else "Identical"),
                delta_color="normal" if delta_auc > 0 else "inverse",
            )

        # Comparative Table
        comp_rows = [
            {
                "Paradigm": "Approach A — Quantitative Only",
                "Features Used": "16 Technical Indicators (Returns, MAs, RSI, MACD, Volatility, BB, ATR)",
                "Val ROC-AUC": q_auc,
                "Val Accuracy": q_val.get("accuracy"),
                "Val F1": q_val.get("f1"),
            },
            {
                "Paradigm": "Approach B — Hybrid (Quant + FinBERT)",
                "Features Used": "16 Technical Indicators + 6 FinBERT Sentiment Features (Pos/Neg/Neu Ratios, Avg Score)",
                "Val ROC-AUC": h_auc,
                "Val Accuracy": h_val.get("accuracy"),
                "Val F1": h_val.get("f1"),
            },
        ]
        st.dataframe(
            pd.DataFrame(comp_rows).style.format({
                "Val ROC-AUC": "{:.4f}",
                "Val Accuracy": "{:.2%}",
                "Val F1": "{:.4f}",
            }),
            use_container_width=True,
            hide_index=True,
        )

        # Empirical Findings Narrative
        st.markdown("#### 🔬 Empirical Analysis of Sentiment Alpha")
        if delta_auc > 0.01:
            st.success(
                f"✅ **Sentiment Contributed Positive Alpha:** The Hybrid model achieved a higher validation ROC-AUC (+{delta_auc:.4f}). "
                "FinBERT sentiment signals provided complementary information not fully captured by price and volume indicators."
            )
        elif delta_auc < -0.01:
            st.warning(
                f"⚠️ **Quantitative Features Outperformed Hybrid:** The Quantitative-only model performed better (-{abs(delta_auc):.4f} ROC-AUC). "
                "This is consistent with the Semi-Strong Form Efficient Market Hypothesis, where widely reported public news is rapidly priced in, "
                "making raw sentiment features noisy for short-term directional prediction."
            )
        else:
            st.info(
                "ℹ️ **Neutral Impact:** The addition of news sentiment yielded comparable performance to purely quantitative features. "
                "Both technical momentum and financial news sentiment reflected similar underlying market sentiment over this observation horizon."
            )

    else:
        st.info(
            "ℹ️ **Hybrid Model Requires News Sentiment:**\n\n"
            "To enable the full Quantitative vs Hybrid comparison:\n"
            "1. Configure a `FINNHUB_API_KEY` or `NEWSAPI_KEY` in `.env`\n"
            "2. Ensure the FinBERT model is loaded and articles are retrieved\n"
            "3. Run an analysis for a ticker with active news coverage."
        )
