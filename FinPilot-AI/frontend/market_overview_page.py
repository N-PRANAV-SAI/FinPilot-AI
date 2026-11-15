"""Global Market Overview Page for FinPilot AI."""
import streamlit as st
import plotly.graph_objects as go
from backend.data.market_data import get_latest_price


GLOBAL_INDICES = [
    {"name": "S&P 500", "ticker": "^GSPC", "country": "United States", "region": "Americas"},
    {"name": "NASDAQ Composite", "ticker": "^IXIC", "country": "United States", "region": "Americas"},
    {"name": "NIFTY 50", "ticker": "^NSEI", "country": "India", "region": "Asia-Pacific"},
    {"name": "BSE SENSEX", "ticker": "^BSESN", "country": "India", "region": "Asia-Pacific"},
    {"name": "FTSE 100", "ticker": "^FTSE", "country": "United Kingdom", "region": "Europe"},
    {"name": "DAX Performance", "ticker": "^GDAXI", "country": "Germany", "region": "Europe"},
    {"name": "NIKKEI 225", "ticker": "^N225", "country": "Japan", "region": "Asia-Pacific"},
    {"name": "Hang Seng", "ticker": "^HSI", "country": "Hong Kong", "region": "Asia-Pacific"},
]


def render_market_overview_page():
    """Render institutional macroeconomic and global exchange monitor."""
    st.markdown("""
        <div style="margin-bottom: 1.5rem;">
            <div style="font-size: 0.85rem; font-weight: 700; color: #38bdf8; text-transform: uppercase; letter-spacing: 1px;">
                Macroeconomic Landscape
            </div>
            <h1 style="margin: 0.2rem 0; font-size: 2.2rem; font-weight: 800; color: #f8fafc;">
                Global Market Overview
            </h1>
            <p style="color: #94a3b8; font-size: 0.95rem;">
                Real-time snapshot of benchmark indices across North America, Europe, India, and Asia-Pacific.
            </p>
        </div>
    """, unsafe_allow_html=True)

    # Grid of global indices
    cols = st.columns(4)
    for idx, item in enumerate(GLOBAL_INDICES):
        with cols[idx % 4]:
            quote = get_latest_price(item["ticker"])
            price = quote.get("price", 0.0) if quote else 0.0
            change = quote.get("change", 0.0) if quote else 0.0
            change_pct = quote.get("change_pct", 0.0) if quote else 0.0
            p_color = "normal" if change >= 0 else "inverse"

            st.metric(
                label=f"{item['name']} ({item['country']})",
                value=f"{price:,.2f}" if price > 0 else "Updating...",
                delta=f"{change:+,.2f} ({change_pct:+.2f}%)" if price > 0 else None,
                delta_color=p_color
            )

    st.markdown("---")

    # Global Market Trading Sessions Status
    st.markdown("### 🌐 Global Exchange Operational Status")
    s_col1, s_col2, s_col3, s_col4 = st.columns(4)
    with s_col1:
        st.markdown("""
            **🇺🇸 NYSE / NASDAQ**  
            Region: New York (EST)  
            *Trading Hours: 09:30 – 16:00 EST*  
            🟢 Active / Order Routing Online
        """)
    with s_col2:
        st.markdown("""
            **🇮🇳 NSE / BSE**  
            Region: Mumbai (IST)  
            *Trading Hours: 09:15 – 15:30 IST*  
            🟢 Active / Order Routing Online
        """)
    with s_col3:
        st.markdown("""
            **🇬🇧 LSE / 🇩🇪 XETRA**  
            Region: London & Frankfurt  
            *Trading Hours: 08:00 – 16:30 UTC*  
            🟢 Active / Order Routing Online
        """)
    with s_col4:
        st.markdown("""
            **🇯🇵 TSE / 🇭🇰 HKEX**  
            Region: Tokyo & Hong Kong  
            *Trading Hours: 09:00 – 15:00 JST*  
            🟢 Active / Order Routing Online
        """)
