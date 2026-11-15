"""Groww-Inspired Clean Home Dashboard for FinPilot AI.
Displays executive portfolio snapshot, global market overview, quick search,
watchlist preview, and AI market insights.
"""
import streamlit as st
import plotly.express as px
from datetime import datetime, timezone
from database.db import get_session
from backend.trading.paper_engine import PaperTradingEngine
from backend.data.market_data import get_latest_price
from backend.data.company_search import search_companies
from database.models import Watchlist, VirtualTransactions


GLOBAL_INDICES = [
    {"name": "S&P 500", "ticker": "^GSPC", "country": "US"},
    {"name": "NIFTY 50", "ticker": "^NSEI", "country": "India"},
    {"name": "DAX", "ticker": "^GDAXI", "country": "Germany"},
    {"name": "NIKKEI 225", "ticker": "^N225", "country": "Japan"},
]


def render_home_page():
    """Render fintech-caliber clean homepage designed for both beginners and pros."""
    user = st.session_state.get("user", {})
    user_id = user.get("user_id", 1)
    user_name = user.get("name", "Investor")

    db = next(get_session())
    try:
        portfolio = PaperTradingEngine.get_user_account_summary(user_id, db)
        watchlist_items = db.query(Watchlist).filter(Watchlist.user_id == user_id).limit(4).all()
        recent_txs = db.query(VirtualTransactions).filter(VirtualTransactions.user_id == user_id).order_by(VirtualTransactions.transaction_date.desc()).limit(3).all()
    finally:
        db.close()

    acc_curr = portfolio.get("account_currency", "INR")
    total_val = portfolio.get("total_portfolio_value", 100000.0)
    avail_cash = portfolio.get("available_cash", 100000.0)
    invested_val = portfolio.get("invested_value", 0.0)
    unrealized_pnl = portfolio.get("unrealized_pnl", 0.0)
    ret_pct = portfolio.get("total_return_pct", 0.0)

    # 1. GREETING & HERO EXECUTIVE CARDS
    st.markdown(f"""
        <div style="margin-bottom: 1.5rem;">
            <div style="display: flex; justify-content: space-between; align-items: flex-end; flex-wrap: wrap; gap: 10px;">
                <div>
                    <span style="font-size: 0.85rem; font-weight: 700; color: #38bdf8; text-transform: uppercase; letter-spacing: 1px;">
                        Global Financial Terminal
                    </span>
                    <h1 style="margin: 2px 0 0; font-size: 2.2rem; font-weight: 800; color: #f8fafc;">
                        Welcome back, {user_name} 👋
                    </h1>
                    <p style="color: #94a3b8; font-size: 0.95rem; margin-top: 4px;">
                        Here is your real-time virtual portfolio and global market summary.
                    </p>
                </div>
                <div style="background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.3); padding: 6px 14px; border-radius: 20px; font-size: 0.85rem; color: #10b981; font-weight: 700;">
                    🛡️ Paper Trading Mode Active
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Main Portfolio Metric Cards
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric(
            label=f"Net Portfolio Worth ({acc_curr})",
            value=f"{acc_curr} {total_val:,.2f}",
            delta=f"{ret_pct:+.2f}% Overall Return"
        )
    with c2:
        st.metric(
            label=f"Available Virtual Cash",
            value=f"{acc_curr} {avail_cash:,.2f}",
            delta="Ready to Deploy",
            delta_color="off"
        )
    with c3:
        st.metric(
            label=f"Invested Equity",
            value=f"{acc_curr} {invested_val:,.2f}",
            delta=f"{len(portfolio.get('holdings', []))} Active Positions",
            delta_color="off"
        )
    with c4:
        pnl_delta_color = "normal" if unrealized_pnl >= 0 else "inverse"
        st.metric(
            label=f"Simulated Profit & Loss",
            value=f"{acc_curr} {unrealized_pnl:+,.2f}",
            delta=f"Realized: {acc_curr} {portfolio.get('realized_pnl', 0.0):+,.2f}",
            delta_color=pnl_delta_color
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # 2. GLOBAL MARKET OVERVIEW TICKER BAR
    st.markdown("### 🌐 Global Market Indices")
    idx_cols = st.columns(4)
    for i, item in enumerate(GLOBAL_INDICES):
        with idx_cols[i]:
            quote = get_latest_price(item["ticker"])
            q_price = quote.get("price", 0.0) if quote else 0.0
            q_chg = quote.get("change", 0.0) if quote else 0.0
            q_pct = quote.get("change_pct", 0.0) if quote else 0.0
            st.metric(
                label=f"{item['name']} ({item['country']})",
                value=f"{q_price:,.2f}" if q_price > 0 else "Online",
                delta=f"{q_chg:+,.2f} ({q_pct:+.2f}%)" if q_price > 0 else None
            )

    st.markdown("<hr style='border-color: #1e293b; margin: 24px 0;'>", unsafe_allow_html=True)

    # 3. FAST GLOBAL SEARCH & BENCHMARK TILES
    col_search, col_ai = st.columns([1.5, 1])

    with col_search:
        st.markdown("### 🔍 Search Global Stocks to Trade")
        query = st.text_input("Enter company or ticker (e.g. Apple, Reliance, Toyota, Siemens, NVIDIA):", key="home_search_input")
        
        if query:
            results = search_companies(query, limit=4)
            if results:
                st.markdown("##### Search Matches:")
                for r in results:
                    r_col1, r_col2 = st.columns([3, 1])
                    with r_col1:
                        st.markdown(f"**{r['name']}** (`{r['ticker']}`) • {r['exchange']} ({r['country']})")
                    with r_col2:
                        if st.button("Explore ↗", key=f"h_exp_{r['ticker']}", use_container_width=True):
                            st.session_state["selected_ticker"] = r["ticker"]
                            st.session_state["nav"] = "Explore"
                            st.rerun()
            else:
                st.caption(f"No direct matches found for '{query}'.")
        else:
            # Popular international shortcuts
            st.markdown("##### 🚀 Popular International Benchmarks:")
            p1, p2, p3, p4 = st.columns(4)
            with p1:
                if st.button("NVIDIA\n(NVDA)", use_container_width=True):
                    st.session_state["selected_ticker"] = "NVDA"
                    st.session_state["nav"] = "Explore"
                    st.rerun()
            with p2:
                if st.button("Reliance\n(RELIANCE.NS)", use_container_width=True):
                    st.session_state["selected_ticker"] = "RELIANCE.NS"
                    st.session_state["nav"] = "Explore"
                    st.rerun()
            with p3:
                if st.button("Toyota\n(7203.T)", use_container_width=True):
                    st.session_state["selected_ticker"] = "7203.T"
                    st.session_state["nav"] = "Explore"
                    st.rerun()
            with p4:
                if st.button("Siemens\n(SIE.DE)", use_container_width=True):
                    st.session_state["selected_ticker"] = "SIE.DE"
                    st.session_state["nav"] = "Explore"
                    st.rerun()

        # Watchlist Preview
        st.markdown("### ⭐ Your Watchlist Preview")
        if watchlist_items:
            for w in watchlist_items:
                w_quote = get_latest_price(w.ticker)
                w_price = w_quote.get("price", 0.0) if w_quote else 0.0
                w_pct = w_quote.get("change_pct", 0.0) if w_quote else 0.0
                w_curr = w.currency or "USD"
                w_color = "#10b981" if w_pct >= 0 else "#f43f5e"
                
                wc1, wc2, wc3 = st.columns([2, 1.5, 1])
                with wc1:
                    st.markdown(f"**{w.company_name}** (`{w.ticker}`)")
                with wc2:
                    st.markdown(f"{w_price:,.2f} {w_curr} <span style='color:{w_color}; font-weight:700;'>({w_pct:+.2f}%)</span>", unsafe_allow_html=True)
                with wc3:
                    if st.button("Trade", key=f"h_tr_{w.id}", use_container_width=True):
                        st.session_state["active_ticker"] = w.ticker
                        st.session_state["nav"] = "Orders"
                        st.rerun()
        else:
            st.caption("No assets in your watchlist yet. Go to **Explore** or **Watchlist** to track companies.")

    with col_ai:
        st.markdown("### 🤖 FinPilot AI Market Insights")
        st.markdown("""
            <div style="background: #0f172a; border: 1px solid #1e293b; border-radius: 12px; padding: 20px; font-size: 0.92rem; line-height: 1.6; color: #cbd5e1; margin-bottom: 1.5rem;">
                <div style="font-weight: 700; color: #38bdf8; margin-bottom: 8px; font-size: 1rem;">
                    💡 Today's Macro Intelligence Brief
                </div>
                • <b>US Equities</b>: High-beta semiconductor and cloud equities remain sensitive to bond yield fluctuations.<br><br>
                • <b>Asia-Pacific Markets</b>: Indian large-caps (Reliance, TCS) demonstrate consistent institutional inflows, offering attractive portfolio diversification.<br><br>
                • <b>Risk Recommendation</b>: Keep at least 15% in cash buffer to take advantage of short-term volatility.
            </div>
        """, unsafe_allow_html=True)

        # Recent Transactions
        st.markdown("### 📜 Recent Paper Trades")
        if recent_txs:
            for t in recent_txs:
                t_color = "#10b981" if t.transaction_type == "BUY" else ("#38bdf8" if t.transaction_type == "SELL" else "#f59e0b")
                st.markdown(f"""
                    <div style="background: #0f172a; border: 1px solid #1e293b; border-radius: 8px; padding: 10px 14px; margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <span style="font-weight: 700; color: {t_color};">{t.transaction_type}</span> 
                            <b>{t.company_name}</b> ({t.ticker})
                        </div>
                        <div style="color: #94a3b8; font-size: 0.85rem;">
                            {t.currency} {t.total_amount:,.2f}
                        </div>
                    </div>
                """, unsafe_allow_html=True)
        else:
            st.caption("No simulated transactions recorded yet.")
