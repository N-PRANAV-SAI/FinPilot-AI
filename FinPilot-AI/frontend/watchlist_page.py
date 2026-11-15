"""Watchlist Page for FinPilot AI."""
import streamlit as st
from database.db import get_session
from database.models import Watchlist
from backend.data.market_data import get_latest_price
from backend.data.company_search import search_companies


def render_watchlist_page():
    """Render user's customizable global stock watchlist."""
    user = st.session_state.get("user", {})
    user_id = user.get("user_id", 1)

    st.markdown("""
        <div style="margin-bottom: 1.5rem;">
            <div style="font-size: 0.85rem; font-weight: 700; color: #38bdf8; text-transform: uppercase; letter-spacing: 1px;">
                Personal Monitor
            </div>
            <h1 style="margin: 0.2rem 0; font-size: 2.2rem; font-weight: 800; color: #f8fafc;">
                Global Asset Watchlist
            </h1>
            <p style="color: #94a3b8; font-size: 0.95rem;">
                Keep track of target assets across US, India, Europe, and Asia before placing paper trades.
            </p>
        </div>
    """, unsafe_allow_html=True)

    db = next(get_session())
    try:
        items = db.query(Watchlist).filter(Watchlist.user_id == user_id).all()
    finally:
        db.close()

    # Add to watchlist bar
    add_col1, add_col2 = st.columns([3, 1])
    with add_col1:
        new_ticker = st.text_input("Add Ticker or Company to Watchlist (e.g. RELIANCE.NS, AAPL, 7203.T):", "")
    with add_col2:
        st.write("")
        st.write("")
        if st.button("➕ Add to Watchlist", use_container_width=True):
            if new_ticker:
                matches = search_companies(new_ticker)
                meta = matches[0] if matches else {"ticker": new_ticker.upper(), "name": new_ticker.upper(), "exchange": "US", "country": "Global", "currency": "USD"}
                
                db = next(get_session())
                try:
                    exists = db.query(Watchlist).filter(Watchlist.user_id == user_id, Watchlist.ticker == meta["ticker"]).first()
                    if not exists:
                        w = Watchlist(
                            user_id=user_id,
                            ticker=meta["ticker"],
                            company_name=meta["name"],
                            exchange=meta["exchange"],
                            country=meta["country"],
                            currency=meta["currency"]
                        )
                        db.add(w)
                        db.commit()
                        st.success(f"Added {meta['name']} ({meta['ticker']}) to your watchlist!")
                        st.rerun()
                    else:
                        st.warning("Company already in watchlist.")
                finally:
                    db.close()

    st.markdown("---")

    if not items:
        st.info("Your watchlist is currently empty. Add stocks like **NVDA**, **RELIANCE.NS**, **TCS.NS**, or **7203.T** above to start monitoring.")
        # Default starter pills
        st.markdown("##### 💡 Suggested Benchmarks to Monitor:")
        s1, s2, s3, s4 = st.columns(4)
        with s1:
            if st.button("➕ Add NVIDIA (NVDA)", use_container_width=True):
                _quick_add(user_id, "NVDA", "NVIDIA Corporation", "NASDAQ", "United States", "USD")
        with s2:
            if st.button("➕ Add Reliance (RELIANCE.NS)", use_container_width=True):
                _quick_add(user_id, "RELIANCE.NS", "Reliance Industries", "NSE", "India", "INR")
        with s3:
            if st.button("➕ Add Toyota (7203.T)", use_container_width=True):
                _quick_add(user_id, "7203.T", "Toyota Motor", "TSE", "Japan", "JPY")
        with s4:
            if st.button("➕ Add Siemens (SIE.DE)", use_container_width=True):
                _quick_add(user_id, "SIE.DE", "Siemens AG", "XETRA", "Germany", "EUR")
        return

    # Watchlist Cards Grid
    cols = st.columns(3)
    for idx, item in enumerate(items):
        with cols[idx % 3]:
            quote = get_latest_price(item.ticker)
            price = quote.get("price", 0.0) if quote else 0.0
            change = quote.get("change", 0.0) if quote else 0.0
            change_pct = quote.get("change_pct", 0.0) if quote else 0.0
            curr = item.currency or quote.get("currency", "USD") if quote else "USD"
            chg_color = "#4ade80" if change >= 0 else "#f87171"

            st.markdown(f"""
                <div style="background: #0f172a; border: 1px solid #1e293b; border-radius: 12px; padding: 18px; margin-bottom: 1rem;">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                        <div>
                            <span style="font-size: 0.75rem; color: #38bdf8; font-weight: 700; text-transform: uppercase;">
                                {item.exchange} • {item.country}
                            </span>
                            <h3 style="margin: 2px 0 0; font-size: 1.15rem; color: #f8fafc;">
                                {item.company_name}
                            </h3>
                            <span style="color: #64748b; font-size: 0.85rem; font-weight: 600;">{item.ticker}</span>
                        </div>
                        <div style="text-align: right;">
                            <span style="font-size: 1.3rem; font-weight: 800; color: #f8fafc;">
                                {price:,.2f} {curr}
                            </span>
                            <div style="color: {chg_color}; font-size: 0.85rem; font-weight: 700;">
                                {change:+,.2f} ({change_pct:+.2f}%)
                            </div>
                        </div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

            btn_col1, btn_col2 = st.columns([1, 1])
            with btn_col1:
                if st.button("Trade Virtually", key=f"trade_{item.id}", use_container_width=True):
                    st.session_state["active_ticker"] = item.ticker
                    st.session_state["nav"] = "Virtual Investing"
                    st.rerun()
            with btn_col2:
                if st.button("Remove", key=f"del_{item.id}", use_container_width=True):
                    db = next(get_session())
                    try:
                        db.query(Watchlist).filter(Watchlist.id == item.id).delete()
                        db.commit()
                        st.rerun()
                    finally:
                        db.close()


def _quick_add(user_id, ticker, name, exchange, country, currency):
    db = next(get_session())
    try:
        w = Watchlist(user_id=user_id, ticker=ticker, company_name=name, exchange=exchange, country=country, currency=currency)
        db.add(w)
        db.commit()
        st.rerun()
    finally:
        db.close()
