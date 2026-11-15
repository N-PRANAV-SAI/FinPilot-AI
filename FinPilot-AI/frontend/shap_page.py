"""SHAP Explainable AI Page for FinPilot AI."""
import streamlit as st
import plotly.graph_objects as go
import pandas as pd


FEATURE_DESCRIPTIONS = {
    "daily_return": "Most recent single-day percentage price change.",
    "weekly_return": "5-day cumulative historical return prior to prediction.",
    "sma20_gap": "Percentage deviation of current price above/below 20-day Simple Moving Average.",
    "sma50_gap": "Percentage deviation of current price above/below 50-day Simple Moving Average.",
    "ema20_gap": "Percentage deviation from 20-day Exponential Moving Average.",
    "rsi14": "14-day Relative Strength Index (overbought >70, oversold <30).",
    "macd": "Moving Average Convergence Divergence line (12 EMA - 26 EMA).",
    "macd_signal": "9-day Exponential Moving Average of the MACD line.",
    "macd_histogram": "MACD momentum spread (MACD line minus Signal line).",
    "volatility20": "Annualized rolling standard deviation of 20-day returns.",
    "momentum10": "10-day rate of price change.",
    "volume_change": "Percentage change in daily trading volume.",
    "bb_position": "Price location within Bollinger Bands (0 = lower band, 1 = upper band).",
    "bb_width": "Normalized width of Bollinger Bands measuring volatility squeeze.",
    "obv_change": "5-day change in On-Balance Volume measuring institutional accumulation.",
    "atr_ratio": "Average True Range normalized by close price (daily price volatility).",
    "revenue_growth": "Reported quarterly revenue growth rate.",
    "profit_margin": "Reported operating profit margin.",
    "eps": "Trailing diluted Earnings Per Share.",
    "debt_to_equity": "Reported financial leverage ratio.",
}


def render_shap():
    """Render SHAP feature importance, waterfall/bar breakdown, and financial interpretation."""
    st.markdown("## 🔬 SHAP Explainable AI (XAI)")
    st.caption("SHapley Additive exPlanations — Game-theoretic attribution of financial features for model predictions.")

    analysis = st.session_state.get("analysis")
    if not analysis:
        st.info("💡 Please run an analysis from the **Dashboard** first.")
        return

    shap_info = analysis.get("shap_info")
    pred = analysis.get("prediction", {})
    training = analysis.get("training", {})
    ticker = analysis["ticker"]

    if not shap_info or not shap_info.get("importances"):
        st.warning(
            f"⚠️ SHAP explanation not yet computed for {ticker}. "
            "Please ensure the analysis completed successfully on the Dashboard."
        )
        return

    selected_model = training.get("selected_model", "Selected Model")
    direction = pred.get("direction", "N/A")
    confidence = pred.get("probability", 0.0)
    base_val = shap_info.get("base_value", 0.5)
    comp_name = analysis.get("company_name", ticker)
    flag = analysis.get("flag", "🌐")
    exchange = analysis.get("exchange", "Exchange")
    country = analysis.get("country", "Global")

    # Explanation Header Banner
    st.markdown(f"""
        <div class="finpilot-card" style="margin-bottom: 1.5rem;">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
                <div>
                    <span style="font-size: 0.85rem; color: #94a3b8; text-transform: uppercase; font-weight: 600;">
                        Interpreting Prediction for {flag} {comp_name} ({ticker}) — {exchange}, {country}
                    </span>
                    <h3 style="margin: 4px 0; color: #f8fafc;">
                        {direction} Output ({confidence:.1%} estimated probability)
                    </h3>
                    <span style="color: #64748b; font-size: 0.9rem;">
                        Explaining: <b>{selected_model}</b> | Explainer Architecture: <b>{shap_info.get('estimator_type', 'Tree/Kernel')}</b>
                    </span>
                </div>
                <div style="text-align: right;">
                    <span style="font-size: 0.85rem; color: #94a3b8;">Baseline Expected Value (E[f(x)]):</span>
                    <div style="font-size: 1.4rem; font-weight: 700; color: #38bdf8;">
                        {base_val:.3f}
                    </div>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Top Positive & Top Negative Driver Columns
    col_pos, col_neg = st.columns(2)
    with col_pos:
        st.markdown("#### 🟢 Top Bullish Drivers (Pushing Toward Positive Return)")
        top_pos = shap_info.get("top_positive", [])
        if top_pos:
            for item in top_pos[:4]:
                feat = item["feature"]
                val = item["contribution"]
                desc = FEATURE_DESCRIPTIONS.get(feat, "Technical indicator feature")
                st.markdown(f"""
                    <div style="background: rgba(16, 185, 129, 0.1); border-left: 3px solid #10b981; padding: 8px 12px; margin-bottom: 8px; border-radius: 0 6px 6px 0;">
                        <div style="display: flex; justify-content: space-between;">
                            <b style="color: #34d399;">{feat}</b>
                            <span style="color: #34d399; font-weight: 700;">+{val:.4f}</span>
                        </div>
                        <div style="font-size: 0.8rem; color: #94a3b8;">{desc}</div>
                    </div>
                """, unsafe_allow_html=True)
        else:
            st.caption("No positive feature attributions.")

    with col_neg:
        st.markdown("#### 🔴 Top Bearish Drivers (Pulling Down Probability)")
        top_neg = shap_info.get("top_negative", [])
        if top_neg:
            for item in top_neg[:4]:
                feat = item["feature"]
                val = item["contribution"]
                desc = FEATURE_DESCRIPTIONS.get(feat, "Technical indicator feature")
                st.markdown(f"""
                    <div style="background: rgba(244, 63, 94, 0.1); border-left: 3px solid #f43f5e; padding: 8px 12px; margin-bottom: 8px; border-radius: 0 6px 6px 0;">
                        <div style="display: flex; justify-content: space-between;">
                            <b style="color: #fb7185;">{feat}</b>
                            <span style="color: #fb7185; font-weight: 700;">{val:.4f}</span>
                        </div>
                        <div style="font-size: 0.8rem; color: #94a3b8;">{desc}</div>
                    </div>
                """, unsafe_allow_html=True)
        else:
            st.caption("No negative feature attributions.")

    st.markdown("---")

    # SHAP Attribution Horizontal Bar Chart
    st.markdown("### Feature Attribution Contribution (SHAP Values)")
    st.caption("Positive SHAP values (green) push the prediction toward Class 1 (positive 5-day return); negative values (red) pull it toward Class 0.")

    importances = shap_info.get("importances", [])
    if importances:
        top_items = importances[:15]
        top_items.reverse()  # Top at top of horizontal chart

        feats = [item["feature"] for item in top_items]
        vals = [item["contribution"] for item in top_items]
        colors = ["#10b981" if v >= 0 else "#f43f5e" for v in vals]

        fig = go.Figure(go.Bar(
            x=vals,
            y=feats,
            orientation="h",
            marker_color=colors,
            text=[f"{v:+.4f}" for v in vals],
            textposition="auto",
        ))
        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            height=480,
            margin=dict(l=0, r=0, t=10, b=0),
            xaxis=dict(title="SHAP Value (Impact on Model Log-Odds / Class Probability)", showgrid=True, gridcolor="#1e293b"),
            yaxis=dict(showgrid=False),
        )
        st.plotly_chart(fig, use_container_width=True)

    # Detailed Plain-Language Attribution Table
    st.markdown("### Detailed Feature Contribution Registry")
    table_rows = []
    for item in importances:
        f_name = item["feature"]
        contrib = item["contribution"]
        table_rows.append({
            "Feature Name": f_name,
            "SHAP Impact": f"{contrib:+.5f}",
            "Direction": "Bullish (+)" if contrib > 0 else ("Bearish (-)" if contrib < 0 else "Neutral"),
            "Description": FEATURE_DESCRIPTIONS.get(f_name, "Model feature"),
        })

    st.dataframe(pd.DataFrame(table_rows), use_container_width=True, hide_index=True)
