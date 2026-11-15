"""Virtual Investing & Paper Trading Interface for FinPilot AI."""
import streamlit as st
from datetime import datetime, timezone
from database.db import get_session
from backend.trading.paper_engine import PaperTradingEngine, get_fx_rate
from backend.data.market_data import get_latest_price
from backend.data.company_search import search_companies
from backend.data.global_exchanges import get_exchange_info, format_currency_amount
from database.models import Holdings, VirtualOrders, VirtualTransactions


def render_virtual_investing_page():
    """Render institutional-grade virtual paper trading dashboard."""
    user = st.session_state.get("user", {})
    user_id = user.get("user_id", 1)

    # Prominent Paper Trading Banner
    st.markdown("""
        <div style="background: linear-gradient(90deg, rgba(245, 158, 11, 0.15), rgba(217, 119, 6, 0.05)); border: 1px solid #f59e0b; border-radius: 12px; padding: 14px 20px; margin-bottom: 1.5rem; display: flex; align-items: center; justify-content: space-between;">
            <div style="display: flex; align-items: center; gap: 12px;">
                <span style="font-size: 1.6rem;">🛡️</span>
                <div>
                    <span style="font-weight: 800; color: #fbbf24; text-transform: uppercase; font-size: 0.85rem; letter-spacing: 1px;">
                        PAPER TRADING ENVIRONMENT — 100% VIRTUAL MONEY
                    </span>
                    <div style="color: #cbd5e1; font-size: 0.85rem; margin-top: 2px;">
                        All transactions are executed using simulated practice capital. Zero real banking or brokerage risk.
                    </div>
                </div>
            </div>
            <div style="background: #1e293b; border: 1px solid #475569; padding: 4px 12px; border-radius: 20px; font-size: 0.75rem; color: #94a3b8; font-weight: 600;">
                LIVE REAL-TIME QUOTES
            </div>
        </div>
    """, unsafe_allow_html=True)

    db = next(get_session())
    try:
        portfolio_summary = PaperTradingEngine.get_user_account_summary(user_id, db)
    finally:
        db.close()

    acc_curr = portfolio_summary.get("account_currency", "INR")
    avail_cash = portfolio_summary.get("available_cash", 0.0)
    total_val = portfolio_summary.get("total_portfolio_value", 0.0)

    # Top Account Summary Bar
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric(
            label=f"Available Cash ({acc_curr})",
            value=f"{acc_curr} {avail_cash:,.2f}"
        )
    with c2:
        st.metric(
            label=f"Total Portfolio Value",
            value=f"{acc_curr} {total_val:,.2f}"
        )
    with c3:
        st.metric(
            label=f"Invested Equity",
            value=f"{acc_curr} {portfolio_summary.get('invested_value', 0.0):,.2f}"
        )
    with c4:
        pnl = portfolio_summary.get("unrealized_pnl", 0.0)
        ret_pct = portfolio_summary.get("total_return_pct", 0.0)
        st.metric(
            label=f"Unrealized P&L",
            value=f"{acc_curr} {pnl:+,.2f}",
            delta=f"{ret_pct:+.2f}%"
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # Main Trading Tabs: Buy / Sell / Pending Orders / Transaction Ledger
    trade_tab, sell_tab, history_tab, reset_tab = st.tabs([
        "🟢 Buy Shares (Virtual Order)",
        "🔴 Sell Holdings",
        "📜 Transaction Ledger & Orders",
        "⚙️ Account Management"
    ])

    # -------------------------------------------------------------
    # TAB 1: BUY SHARES
    # -------------------------------------------------------------
    with trade_tab:
        col_ticket, col_preview = st.columns([1.2, 1])

        # Active ticker from session state or default
        active_analysis = st.session_state.get("active_analysis")
        default_ticker = active_analysis.get("ticker", "NVDA") if active_analysis else "NVDA"

        with col_ticket:
            st.markdown("### 🛒 Place Simulated Buy Order")

            # Search / Select Company
            search_query = st.text_input("Enter Company Name or Ticker to Trade:", value=default_ticker)
            matches = search_companies(search_query) if search_query else []

            if matches:
                selected_match = matches[0]
                ticker_to_trade = selected_match["ticker"]
                comp_name = selected_match["name"]
                exchange = selected_match["exchange"]
                country = selected_match["country"]
                curr_asset = selected_match["currency"]
            else:
                ticker_to_trade = search_query.strip().upper()
                comp_name = ticker_to_trade
                exchange = "US"
                country = "United States"
                curr_asset = "USD"

            # Fetch live quote
            quote = get_latest_price(ticker_to_trade)
            live_price = quote.get("price") if quote else None
            asset_currency = (curr_asset or quote.get("currency") or "USD").upper()

            if live_price is None or live_price <= 0:
                st.error(f"❌ Real-time market price for **{ticker_to_trade}** is currently unavailable. Orders are disabled to prevent fabricated pricing.")
            else:
                st.success(f"📈 **Live Market Quote**: **{live_price:,.2f} {asset_currency}** ({exchange})")

                # FX Calculation
                fx_rate = get_fx_rate(asset_currency, acc_curr)

                order_type = st.radio("Order Type:", ["MARKET", "LIMIT"], horizontal=True)

                limit_price_val = None
                if order_type == "LIMIT":
                    limit_price_val = st.number_input(
                        f"Limit Target Price ({asset_currency}):",
                        min_value=0.01,
                        value=round(live_price * 0.98, 2),
                        step=0.1
                    )
                    st.caption("A buy limit order will execute only when the market price touches or falls below this target.")

                input_mode = st.radio("Specify Order by:", ["Investment Amount", "Number of Shares"], horizontal=True)

                if input_mode == "Investment Amount":
                    inv_amt = st.number_input(
                        f"Amount to Invest ({acc_curr}):",
                        min_value=100.0 if acc_curr == "INR" else 10.0,
                        max_value=float(avail_cash) if avail_cash > 0 else 1000.0,
                        value=min(10000.0 if acc_curr == "INR" else 500.0, float(avail_cash) if avail_cash > 0 else 1000.0),
                        step=500.0 if acc_curr == "INR" else 50.0
                    )
                    eff_price = limit_price_val if order_type == "LIMIT" and limit_price_val else live_price
                    shares_est = round((inv_amt / fx_rate) / eff_price, 4)
                    total_req_acc = inv_amt
                else:
                    shares_est = st.number_input(
                        "Number of Shares:",
                        min_value=0.01,
                        value=1.0,
                        step=1.0
                    )
                    eff_price = limit_price_val if order_type == "LIMIT" and limit_price_val else live_price
                    total_req_acc = shares_est * eff_price * fx_rate

                with col_preview:
                    st.markdown("### 📋 Order Confirmation Ticket")
                    st.markdown(f"""
                        <div style="background: #0f172a; border: 1px solid #1e293b; border-radius: 12px; padding: 18px; margin-bottom: 1rem;">
                            <div style="font-size: 1.2rem; font-weight: 700; color: #f8fafc; margin-bottom: 12px;">
                                {comp_name} ({ticker_to_trade})
                            </div>
                            <div style="display: flex; justify-content: space-between; margin-bottom: 8px; color: #94a3b8; font-size: 0.9rem;">
                                <span>Exchange & Country</span>
                                <b style="color: #f1f5f9;">{exchange} ({country})</b>
                            </div>
                            <div style="display: flex; justify-content: space-between; margin-bottom: 8px; color: #94a3b8; font-size: 0.9rem;">
                                <span>Order Type</span>
                                <b style="color: #38bdf8;">{order_type} ORDER</b>
                            </div>
                            <div style="display: flex; justify-content: space-between; margin-bottom: 8px; color: #94a3b8; font-size: 0.9rem;">
                                <span>Execution Quote</span>
                                <b style="color: #f1f5f9;">{eff_price:,.2f} {asset_currency}</b>
                            </div>
                            <div style="display: flex; justify-content: space-between; margin-bottom: 8px; color: #94a3b8; font-size: 0.9rem;">
                                <span>Estimated Shares</span>
                                <b style="color: #38bdf8;">{shares_est}</b>
                            </div>
                            <div style="display: flex; justify-content: space-between; margin-bottom: 8px; color: #94a3b8; font-size: 0.9rem;">
                                <span>Applied FX Rate</span>
                                <b style="color: #f1f5f9;">1 {asset_currency} = {fx_rate:.4f} {acc_curr}</b>
                            </div>
                            <div style="display: flex; justify-content: space-between; margin-bottom: 8px; color: #94a3b8; font-size: 0.9rem;">
                                <span>Simulated Brokerage Fee</span>
                                <b style="color: #4ade80;">{acc_curr} 0.00 (Zero Fee)</b>
                            </div>
                            <hr style="border: 0; border-top: 1px solid #334155; margin: 12px 0;">
                            <div style="display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 1.05rem; font-weight: 700;">
                                <span style="color: #f8fafc;">Total Order Cost</span>
                                <span style="color: #38bdf8;">{acc_curr} {total_req_acc:,.2f}</span>
                            </div>
                            <div style="display: flex; justify-content: space-between; color: #94a3b8; font-size: 0.85rem;">
                                <span>Remaining Virtual Cash</span>
                                <b>{acc_curr} {max(0.0, avail_cash - total_req_acc):,.2f}</b>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)

                    btn_buy = st.button("🚀 Confirm & Execute Virtual Buy Order", use_container_width=True, type="primary")

                    if btn_buy:
                        db = next(get_session())
                        try:
                            exec_res = PaperTradingEngine.execute_buy_order(
                                user_id=user_id,
                                ticker=ticker_to_trade,
                                company_name=comp_name,
                                exchange=exchange,
                                country=country,
                                currency=asset_currency,
                                order_type=order_type,
                                quantity=shares_est,
                                limit_price=limit_price_val,
                                db=db
                            )
                            if exec_res.get("success"):
                                st.success(f"🎉 {exec_res.get('message')}")
                                st.balloons()
                                st.rerun()
                            else:
                                st.error(f"❌ {exec_res.get('error')}")
                        finally:
                            db.close()

    # -------------------------------------------------------------
    # TAB 2: SELL HOLDINGS
    # -------------------------------------------------------------
    with sell_tab:
        st.markdown("### 🔴 Liquidate / Sell Existing Holdings")
        holdings = portfolio_summary.get("holdings", [])

        if not holdings:
            st.info("You currently do not own any shares in your virtual portfolio. Go to the **Buy Shares** tab to purchase global stocks.")
        else:
            holding_options = {f"{h['ticker']} — {h['company_name']} ({h['quantity']} shares)": h for h in holdings}
            selected_holding_label = st.selectbox("Select Holding to Sell:", list(holding_options.keys()))
            selected_h = holding_options[selected_holding_label]

            s_col1, s_col2 = st.columns(2)
            with s_col1:
                st.markdown(f"""
                    - **Current Shares Owned**: **{selected_h['quantity']}**
                    - **Average Purchase Price**: **{selected_h['average_cost']:.2f} {selected_h['asset_currency']}**
                    - **Current Market Price**: **{selected_h['current_price']:.2f} {selected_h['asset_currency']}**
                    - **Current Position Value**: **{acc_curr} {selected_h['current_value_acc']:,.2f}**
                    - **Unrealized P&L**: **{acc_curr} {selected_h['unrealized_pnl_acc']:+,.2f} ({selected_h['pnl_pct']:+.2f}%)**
                """)

            with s_col2:
                sell_qty = st.number_input(
                    "Quantity to Sell:",
                    min_value=0.0001,
                    max_value=float(selected_h["quantity"]),
                    value=float(selected_h["quantity"]),
                    step=1.0
                )
                est_proceeds_acc = sell_qty * selected_h["current_price"] * selected_h["fx_rate_applied"]
                cost_basis_sold_acc = sell_qty * selected_h["average_cost"] * selected_h["fx_rate_applied"]
                realized_pnl_est = est_proceeds_acc - cost_basis_sold_acc

                st.markdown(f"""
                    **Estimated Proceeds**: {acc_curr} {est_proceeds_acc:,.2f}  
                    **Estimated Realized P&L**: <span style="color: {'#4ade80' if realized_pnl_est >= 0 else '#f87171'}; font-weight: 700;">{acc_curr} {realized_pnl_est:+,.2f}</span>
                """, unsafe_allow_html=True)

                if st.button("Confirm Virtual Sale", type="primary", use_container_width=True):
                    db = next(get_session())
                    try:
                        sell_res = PaperTradingEngine.execute_sell_order(
                            user_id=user_id,
                            ticker=selected_h["ticker"],
                            quantity=sell_qty,
                            db=db
                        )
                        if sell_res.get("success"):
                            st.success(sell_res.get("message"))
                            st.rerun()
                        else:
                            st.error(sell_res.get("error"))
                    finally:
                        db.close()

    # -------------------------------------------------------------
    # TAB 3: TRANSACTION LEDGER & ORDERS
    # -------------------------------------------------------------
    with history_tab:
        st.markdown("### 📜 Simulated Orders & Execution Log")

        db = next(get_session())
        try:
            txs = db.query(VirtualTransactions).filter(VirtualTransactions.user_id == user_id).order_by(VirtualTransactions.transaction_date.desc()).all()
            orders = db.query(VirtualOrders).filter(VirtualOrders.user_id == user_id).order_by(VirtualOrders.created_at.desc()).all()
        finally:
            db.close()

        if txs:
            st.markdown("#### Completed Transactions")
            tx_data = [
                {
                    "Date (UTC)": t.transaction_date.strftime("%Y-%m-%d %H:%M") if t.transaction_date else "N/A",
                    "Type": t.transaction_type,
                    "Asset": f"{t.company_name} ({t.ticker})",
                    "Quantity": f"{t.quantity:.4f}" if t.quantity > 0 else "-",
                    "Exec Price": f"{t.price:.2f}" if t.price > 0 else "-",
                    "Total Amount": f"{t.currency} {t.total_amount:,.2f}",
                    "Realized P&L": f"{t.currency} {t.realized_pnl:+,.2f}" if t.transaction_type == "SELL" else "-"
                }
                for t in txs
            ]
            st.dataframe(tx_data, use_container_width=True)
        else:
            st.info("No transaction records found yet.")

    # -------------------------------------------------------------
    # TAB 4: ACCOUNT MANAGEMENT
    # -------------------------------------------------------------
    with reset_tab:
        st.markdown("### ⚙️ Virtual Account Settings")

        m1, m2 = st.columns(2)
        with m1:
            st.markdown("#### 💰 Add Virtual Practice Funds")
            st.caption("Need more fake cash to test a larger portfolio strategy?")
            add_amt = st.number_input(f"Virtual Funds to Add ({acc_curr}):", min_value=1000.0, value=50000.0, step=10000.0)
            if st.button(f"Add {acc_curr} {add_amt:,.2f} (Virtual)", use_container_width=True):
                db = next(get_session())
                try:
                    res = PaperTradingEngine.add_virtual_funds(user_id, add_amt, db)
                    if res.get("success"):
                        st.success(res.get("message"))
                        st.rerun()
                finally:
                    db.close()

        with m2:
            st.markdown("#### 🔄 Reset Practice Account")
            st.caption("Clears all current holdings and resets your available cash balance to a chosen amount.")
            new_bal = st.number_input(f"Reset Balance to ({acc_curr}):", min_value=10000.0, value=100000.0, step=10000.0)
            if st.button("⚠️ Reset Entire Virtual Account", type="secondary", use_container_width=True):
                db = next(get_session())
                try:
                    res = PaperTradingEngine.reset_virtual_account(user_id, new_bal, db)
                    if res.get("success"):
                        st.success(res.get("message"))
                        st.rerun()
                finally:
                    db.close()
