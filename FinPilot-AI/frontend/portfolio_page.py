"""Virtual Portfolio Management Dashboard for FinPilot AI."""
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from database.db import get_session
from backend.trading.paper_engine import PaperTradingEngine
from backend.data.global_exchanges import format_currency_amount


def render_portfolio_page():
    """Render comprehensive multi-asset portfolio analytics & risk breakdown."""
    user = st.session_state.get("user", {})
    user_id = user.get("user_id", 1)

    st.markdown("""
        <div style="margin-bottom: 1.5rem;">
            <div style="font-size: 0.85rem; font-weight: 700; color: #38bdf8; text-transform: uppercase; letter-spacing: 1px;">
                Virtual Asset Management
            </div>
            <h1 style="margin: 0.2rem 0; font-size: 2.2rem; font-weight: 800; color: #f8fafc;">
                My Virtual Portfolio
            </h1>
            <p style="color: #94a3b8; font-size: 0.95rem;">
                Track multi-currency global holdings, simulated asset allocation, and concentration risk metrics.
            </p>
        </div>
    """, unsafe_allow_html=True)

    db = next(get_session())
    try:
        portfolio = PaperTradingEngine.get_user_account_summary(user_id, db)
    finally:
        db.close()

    acc_curr = portfolio.get("account_currency", "INR")
    total_val = portfolio.get("total_portfolio_value", 0.0)
    avail_cash = portfolio.get("available_cash", 0.0)
    invested_val = portfolio.get("invested_value", 0.0)
    unrealized_pnl = portfolio.get("unrealized_pnl", 0.0)
    realized_pnl = portfolio.get("realized_pnl", 0.0)
    ret_pct = portfolio.get("total_return_pct", 0.0)
    holdings = portfolio.get("holdings", [])
    risk = portfolio.get("risk_metrics", {})

    # Top Executive Portfolio Cards
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric(
            label=f"Net Portfolio Worth ({acc_curr})",
            value=f"{acc_curr} {total_val:,.2f}",
            delta=f"{ret_pct:+.2f}% All-Time Return"
        )
    with c2:
        st.metric(
            label=f"Available Cash ({acc_curr})",
            value=f"{acc_curr} {avail_cash:,.2f}",
            delta="Ready to Deploy",
            delta_color="off"
        )
    with c3:
        st.metric(
            label=f"Invested Equity ({acc_curr})",
            value=f"{acc_curr} {invested_val:,.2f}",
            delta=f"{len(holdings)} Global Positions",
            delta_color="off"
        )
    with c4:
        pnl_color = "normal" if unrealized_pnl >= 0 else "inverse"
        st.metric(
            label=f"Unrealized P&L ({acc_curr})",
            value=f"{acc_curr} {unrealized_pnl:+,.2f}",
            delta=f"Realized: {acc_curr} {realized_pnl:+,.2f}",
            delta_color=pnl_color
        )

    st.markdown("<br>", unsafe_allow_html=True)

    if not holdings:
        st.info("💡 **Your portfolio is currently 100% in cash.** Go to the **Virtual Investing** tab to purchase shares of companies like Apple, NVIDIA, Reliance Industries, or Toyota using your practice funds!")
        return

    # Visual Analytics: Allocation & Performance Charts
    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        st.markdown("### 🥧 Asset & Country Allocation")
        country_exp = risk.get("country_exposure", {})
        if country_exp:
            labels = list(country_exp.keys()) + ["Cash"]
            values = list(country_exp.values()) + [round(avail_cash / total_val * 100, 1)]
            fig_alloc = px.pie(
                names=labels,
                values=values,
                hole=0.45,
                color_discrete_sequence=px.colors.qualitative.Prism
            )
            fig_alloc.update_layout(
                template="plotly_dark",
                margin=dict(l=10, r=10, t=10, b=10),
                paper_bgcolor="rgba(0,0,0,0)",
                legend=dict(orientation="h", yanchor="bottom", y=-0.2)
            )
            st.plotly_chart(fig_alloc, use_container_width=True)

    with chart_col2:
        st.markdown("### 📊 Profit & Loss by Position")
        pnl_data = [
            {
                "Company": f"{h['company_name']} ({h['ticker']})",
                "P&L": h["unrealized_pnl_acc"],
                "Color": "#4ade80" if h["unrealized_pnl_acc"] >= 0 else "#f87171"
            }
            for h in holdings
        ]
        fig_pnl = go.Figure()
        fig_pnl.add_trace(go.Bar(
            y=[d["Company"] for d in pnl_data],
            x=[d["P&L"] for d in pnl_data],
            orientation='h',
            marker=dict(color=[d["Color"] for d in pnl_data])
        ))
        fig_pnl.update_layout(
            template="plotly_dark",
            margin=dict(l=10, r=10, t=10, b=10),
            paper_bgcolor="rgba(0,0,0,0)",
            xaxis_title=f"Unrealized P&L ({acc_curr})"
        )
        st.plotly_chart(fig_pnl, use_container_width=True)

    # Detailed Holdings Table
    st.markdown("### 📋 Active Global Holdings")
    table_rows = []
    for h in holdings:
        table_rows.append({
            "Ticker": h["ticker"],
            "Company": h["company_name"],
            "Exchange": h["exchange"],
            "Country": h["country"],
            "Shares": f"{h['quantity']:.4f}",
            "Avg Price": f"{h['average_cost']:.2f} {h['asset_currency']}",
            "Current Price": f"{h['current_price']:.2f} {h['asset_currency']}",
            f"Value ({acc_curr})": f"{acc_curr} {h['current_value_acc']:,.2f}",
            f"P&L ({acc_curr})": f"{acc_curr} {h['unrealized_pnl_acc']:+,.2f}",
            "Return %": f"{h['pnl_pct']:+.2f}%"
        })
    st.dataframe(table_rows, use_container_width=True)

    # Portfolio Risk & Concentration Card
    st.markdown("### 🛡️ Institutional Risk & Diversification Assessment")
    r1, r2, r3, r4 = st.columns(4)
    with r1:
        st.metric(label="Concentration Risk", value=risk.get("concentration_risk", "Moderate"))
    with r2:
        st.metric(label="Top Asset Weight", value=f"{risk.get('max_holding_pct', 0.0):.1f}%")
    with r3:
        st.metric(label="Herfindahl Index (HHI)", value=f"{risk.get('hhi_index', 0.0):.0f}")
    with r4:
        st.metric(label="Diversification Status", value="Healthy" if len(holdings) >= 4 else "Needs More Assets")

    st.caption("ℹ️ **Risk Definition**: HHI above 2,500 indicates high portfolio concentration. Spreading investments across 5+ global sectors reduces single-stock vulnerability.")
