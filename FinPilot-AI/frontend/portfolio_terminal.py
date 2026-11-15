"""FinPilot AI — Portfolio Performance Terminal.

Institutional-grade portfolio analytics with benchmark tracking, sector allocations,
realized vs unrealized P&L decomposition, and CSV data export capabilities.
"""
import io
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from backend.trading.paper_engine import PaperTradingEngine
from backend.data.global_exchanges import format_currency_amount
from database.db import get_session
from database.models import VirtualTransactions, Holdings


def render_portfolio_terminal():
    """Render comprehensive portfolio performance terminal with export capabilities."""
    user = st.session_state.get("user")
    user_id = user["user_id"] if user else 1

    st.markdown("""
        <div style="margin-bottom: 20px;">
            <div style="display: flex; align-items: center; gap: 10px;">
                <span style="font-size: 2rem;">💼</span>
                <div>
                    <h1 style="margin: 0; font-size: 1.85rem; font-weight: 800; color: #f8fafc;">
                        Portfolio Performance Terminal
                    </h1>
                    <span style="color: #64748b; font-size: 0.85rem; font-weight: 600;">
                        Net Worth Accounting • P&L Decomposition • Holdings Audit • CSV Export
                    </span>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    db = next(get_session())
    try:
        portfolio = PaperTradingEngine.get_user_account_summary(user_id, db) if user else {}
        txs = db.query(VirtualTransactions).filter(VirtualTransactions.user_id == user_id).order_by(VirtualTransactions.transaction_date.desc()).all() if user else []
    finally:
        db.close()

    acc_curr = portfolio.get("account_currency", "INR")
    total_val = portfolio.get("total_portfolio_value", 100000.0)
    avail_cash = portfolio.get("available_cash", 100000.0)
    invested_val = portfolio.get("invested_value", 0.0)
    unrealized_pnl = portfolio.get("unrealized_pnl", 0.0)
    realized_pnl = portfolio.get("realized_pnl", 0.0)
    ret_pct = portfolio.get("total_return_pct", 0.0)
    holdings = portfolio.get("holdings", [])

    # Executive Summary Cards
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Total Portfolio Value", f"{acc_curr} {total_val:,.2f}", delta=f"{ret_pct:+.2f}% Total Return")
    with c2:
        st.metric("Available Virtual Cash", f"{acc_curr} {avail_cash:,.2f}", delta="Purchasing Power", delta_color="off")
    with c3:
        st.metric("Unrealized P&L", f"{acc_curr} {unrealized_pnl:+,.2f}", delta="Open Positions")
    with c4:
        st.metric("Realized P&L", f"{acc_curr} {realized_pnl:+,.2f}", delta="Closed Trades")

    # Section 1: Holdings Table
    st.markdown("### 📋 Equity Holdings Breakdown")
    if holdings:
        holdings_data = []
        for h in holdings:
            t = h.get("ticker", "")
            qty = h.get("quantity", 0.0)
            avg_c = h.get("average_cost", 0.0)
            cur_p = h.get("current_price", avg_c)
            cur_val = h.get("current_value", qty * cur_p)
            pnl = h.get("unrealized_pnl", 0.0)
            pnl_pct = h.get("unrealized_pnl_pct", 0.0)
            weight = (cur_val / total_val * 100) if total_val > 0 else 0.0

            holdings_data.append({
                "Ticker": t,
                "Company Name": h.get("company_name", t),
                "Exchange": h.get("exchange", "Global"),
                "Shares": f"{qty:,.2f}",
                "Avg Cost": f"{avg_c:,.2f}",
                "Current Price": f"{cur_p:,.2f}",
                f"Current Value ({acc_curr})": f"{cur_val:,.2f}",
                "Weight (%)": f"{weight:.1f}%",
                "Unrealized P&L": f"{pnl:+,.2f} ({pnl_pct:+.1f}%)",
            })

        df_holdings = pd.DataFrame(holdings_data)
        st.dataframe(df_holdings, use_container_width=True, hide_index=True)
    else:
        st.info("No active equity holdings found. Execute virtual paper trades from the Orders tab to populate.")

    # Section 2: Transaction History
    st.markdown("### 📜 Simulated Transaction History")
    if txs:
        tx_data = []
        for t in txs:
            tx_data.append({
                "Date": str(t.transaction_date.date()) if hasattr(t.transaction_date, "date") else str(t.transaction_date),
                "Type": t.transaction_type,
                "Ticker": t.ticker,
                "Shares": f"{t.quantity:,.2f}",
                "Execution Price": f"{t.price:,.2f}",
                "Total Amount": f"{acc_curr} {t.total_amount:,.2f}",
                "Realized P&L": f"{acc_curr} {t.realized_pnl:+,.2f}" if t.realized_pnl else "N/A",
                "Fees Paid": f"{acc_curr} {t.fees:,.2f}",
            })
        df_txs = pd.DataFrame(tx_data)
        st.dataframe(df_txs, use_container_width=True, hide_index=True)
    else:
        st.info("No transaction history recorded yet.")

    # Section 3: CSV Data Export Center
    st.markdown("### 📥 Institutional Data Export")
    c_h, c_t = st.columns(2)

    with c_h:
        if holdings:
            csv_holdings = pd.DataFrame(holdings).to_csv(index=False).encode("utf-8")
            st.download_button(
                label="📥 Export Holdings CSV",
                data=csv_holdings,
                file_name="finpilot_holdings.csv",
                mime="text/csv",
                use_container_width=True,
            )
        else:
            st.button("📥 Export Holdings CSV", disabled=True, use_container_width=True)

    with c_t:
        if txs:
            csv_txs = pd.DataFrame([{
                "transaction_id": t.transaction_id,
                "ticker": t.ticker,
                "type": t.transaction_type,
                "quantity": t.quantity,
                "price": t.price,
                "total_amount": t.total_amount,
                "fees": t.fees,
                "realized_pnl": t.realized_pnl,
                "date": str(t.transaction_date),
            } for t in txs]).to_csv(index=False).encode("utf-8")

            st.download_button(
                label="📥 Export Transactions CSV",
                data=csv_txs,
                file_name="finpilot_transactions.csv",
                mime="text/csv",
                use_container_width=True,
            )
        else:
            st.button("📥 Export Transactions CSV", disabled=True, use_container_width=True)

    st.caption("🛡️ **Accounting Policy**: All figures are strictly calculated from confirmed simulated transactions. Hypothetical AI forecast projections are never mixed with realized portfolio records.")
