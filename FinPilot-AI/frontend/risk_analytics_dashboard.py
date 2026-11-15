"""FinPilot AI — Portfolio Risk Analytics Dashboard.

Provides institutional risk measures: VaR 95%, CVaR, Sharpe, Sortino, HHI concentration,
asset correlation heatmap, and historical macroeconomic stress test projections.
"""
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

from backend.analytics.risk_analytics import compute_portfolio_risk_analytics
from backend.trading.paper_engine import PaperTradingEngine
from database.db import get_session

SAMPLE_DEMO_HOLDINGS = [
    {"ticker": "NVDA", "quantity": 10, "current_value": 12850.0},
    {"ticker": "AAPL", "quantity": 15, "current_value": 33645.0},
    {"ticker": "RELIANCE.NS", "quantity": 10, "current_value": 29805.0},
    {"ticker": "MSFT", "quantity": 5, "current_value": 21260.0},
]


def render_risk_analytics_dashboard():
    """Render comprehensive portfolio risk management terminal."""
    user = st.session_state.get("user")
    user_id = user["user_id"] if user else 1

    st.markdown("""
        <div style="margin-bottom: 20px;">
            <div style="display: flex; align-items: center; gap: 10px;">
                <span style="font-size: 2rem;">⚡</span>
                <div>
                    <h1 style="margin: 0; font-size: 1.85rem; font-weight: 800; color: #f8fafc;">
                        Risk Analytics & Stress Testing
                    </h1>
                    <span style="color: #64748b; font-size: 0.85rem; font-weight: 600;">
                        Value at Risk (VaR) • Expected Shortfall (CVaR) • Stress Scenarios • Correlation Matrix
                    </span>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Fetch live user holdings from database
    db = next(get_session())
    try:
        portfolio = PaperTradingEngine.get_user_account_summary(user_id, db) if user else {}
    finally:
        db.close()

    holdings = portfolio.get("holdings", [])
    acc_curr = portfolio.get("account_currency", "INR")
    total_val = portfolio.get("total_portfolio_value", 100000.0)
    avail_cash = portfolio.get("available_cash", 100000.0)

    # Offer Demo Mode toggle if user has no positions
    use_sample = False
    if not holdings:
        st.info("💡 Your virtual account currently holds 100% cash. Displaying institutional sample equity portfolio for analysis below.")
        holdings = SAMPLE_DEMO_HOLDINGS
        total_val = sum(h["current_value"] for h in holdings) + 20000.0
        avail_cash = 20000.0
        use_sample = True

    # Compute risk analytics
    with st.spinner("Calculating multi-asset covariance and Value at Risk distributions..."):
        risk = compute_portfolio_risk_analytics(
            holdings=holdings,
            account_currency=acc_curr,
            total_portfolio_value=total_val,
            available_cash=avail_cash,
        )

    m = risk["metrics"]

    # Top Executive Risk KPI Grid
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(
            "1-Day VaR (95%)",
            f"{m['var_95_daily_pct']:.2f}%",
            delta=f"-{acc_curr} {m['var_95_daily_amt']:,.0f}",
            delta_color="inverse",
            help="Maximum estimated 1-day loss under normal market conditions with 95% confidence",
        )
    with col2:
        st.metric(
            "1-Day CVaR (Tail Risk)",
            f"{m['cvar_95_daily_pct']:.2f}%",
            delta=f"-{acc_curr} {m['cvar_95_daily_amt']:,.0f}",
            delta_color="inverse",
            help="Expected shortfall if the 95% VaR threshold is breached",
        )
    with col3:
        st.metric(
            "Portfolio Volatility",
            f"{m['portfolio_volatility_ann_pct']:.1f}%",
            delta=f"Beta: {m['beta_vs_benchmark']:.2f}",
            help="Annualized portfolio standard deviation (252 sessions)",
        )
    with col4:
        st.metric(
            "HHI Concentration",
            f"{m['hhi_concentration']:.3f}",
            delta=m["concentration_tier"],
            help="Herfindahl-Hirschman Index (<0.15 is highly diversified)",
        )

    # Section 1: Asset Allocation & Correlation Heatmap
    st.markdown("### 📊 Asset Allocation & Markowitz Correlation Matrix")
    c_pie, c_corr = st.columns([1, 2])

    with c_pie:
        # Donut Chart
        alloc_labels = [h["ticker"] for h in holdings] + (["Cash"] if avail_cash > 0 else [])
        alloc_vals = [h.get("current_value", 0.0) for h in holdings] + ([avail_cash] if avail_cash > 0 else [])
        fig_donut = go.Figure(data=[go.Pie(labels=alloc_labels, values=alloc_vals, hole=0.55, marker_colors=["#38bdf8", "#818cf8", "#10b981", "#f59e0b", "#94a3b8"])])
        fig_donut.update_layout(
            template="plotly_dark",
            plot_bgcolor="#0f172a",
            paper_bgcolor="#0f172a",
            margin=dict(l=0, r=0, t=10, b=0),
            height=280,
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
        )
        st.plotly_chart(fig_donut, use_container_width=True)

    with c_corr:
        corr_matrix = risk.get("correlation_matrix", {})
        if corr_matrix and len(corr_matrix) >= 2:
            corr_df = pd.DataFrame(corr_matrix)
            fig_heatmap = px.imshow(
                corr_df,
                text_auto=".2f",
                aspect="auto",
                color_continuous_scale="RdBu_r",
                zmin=-1.0,
                zmax=1.0,
            )
            fig_heatmap.update_layout(
                template="plotly_dark",
                plot_bgcolor="#0f172a",
                paper_bgcolor="#0f172a",
                margin=dict(l=0, r=0, t=10, b=0),
                height=280,
            )
            st.plotly_chart(fig_heatmap, use_container_width=True)
        else:
            st.info("Correlation matrix requires at least 2 active portfolio equity assets.")

    # Section 2: Historical Macroeconomic Stress Testing
    st.markdown("### 🌪️ Historical Macroeconomic Stress Scenarios")
    st.caption("Hypothetical portfolio impact projected by subjecting your current equity beta and factor weights to landmark historical shocks.")

    stress_tests = risk.get("stress_tests", [])
    if stress_tests:
        stress_df = pd.DataFrame([
            {
                "Crisis Event": s["name"],
                "Historical Period": s["period"],
                "Market Index Drawdown": f"{s['market_shock_pct']:.1f}%",
                "Est. Portfolio Impact": f"{s['portfolio_impact_pct']:+.1f}%",
                f"Est. Monetary Loss ({acc_curr})": f"-{acc_curr} {s['portfolio_loss_amt']:,.0f}",
                "Macro Mechanism": s["description"],
            }
            for s in stress_tests
        ])
        st.dataframe(stress_df, use_container_width=True, hide_index=True)

    # Section 3: Educational Methodology & Assumptions
    st.markdown("### 📚 Risk Metric Methodology & Governance Disclosures")
    explanations = risk.get("explanations", {})

    for key, info in explanations.items():
        with st.expander(f"📖 {info['title']}"):
            st.markdown(f"**Definition:** {info['definition']}")
            st.markdown(f"**Why Investors Use It:** {info['why_it_matters']}")
            st.markdown(f"**Mathematical Formula:** `{info['formula']}`")
            st.markdown(f"⚠️ **Limitations:** {info['limitations']}")

    st.caption(f"🛡️ **Assumptions**: Risk-free benchmark rate = {risk['assumptions']['risk_free_rate_ann_pct']:.2f}% annualized • VaR horizon = {risk['assumptions']['var_horizon']} • Annualization = {risk['assumptions']['annualization_factor']}.")
