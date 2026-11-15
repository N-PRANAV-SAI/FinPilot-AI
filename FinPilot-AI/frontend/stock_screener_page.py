"""FinPilot AI — Stock Screener & Asset Comparison Page.

Filters global multi-exchange universe across fundamental and technical metrics.
Enables side-by-side multi-company comparison tables and charts.
"""
import streamlit as st
import pandas as pd
from backend.analytics.screener import screen_stocks, compare_companies_side_by_side

SECTORS = ["All Sectors", "Technology", "Consumer Cyclical", "Energy", "Financial Services", "Communication Services", "Industrials"]
COUNTRIES = ["All Countries", "United States", "India", "Japan", "Germany", "United Kingdom", "Hong Kong", "South Korea"]
EXCHANGES = ["All Exchanges", "NASDAQ", "NSE", "TSE", "XETRA", "LSE", "HKEX", "KRX"]


def render_stock_screener_page():
    """Render global multi-exchange stock screener and comparison terminal."""
    st.markdown("""
        <div style="margin-bottom: 20px;">
            <div style="display: flex; align-items: center; gap: 10px;">
                <span style="font-size: 2rem;">🔍</span>
                <div>
                    <h1 style="margin: 0; font-size: 1.85rem; font-weight: 800; color: #f8fafc;">
                        Global Stock Screener & Comparison
                    </h1>
                    <span style="color: #64748b; font-size: 0.85rem; font-weight: 600;">
                        Multi-Exchange Filters • Valuation Multiples • Side-by-Side Financial Comparison
                    </span>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    tab_screen, tab_compare = st.tabs(["🔎 Stock Screener", "⚖️ Multi-Company Comparison"])

    with tab_screen:
        # Filter Configuration
        f1, f2, f3, f4 = st.columns(4)
        with f1:
            sel_sector = st.selectbox("Sector", SECTORS, index=0)
        with f2:
            sel_country = st.selectbox("Country", COUNTRIES, index=0)
        with f3:
            sel_exchange = st.selectbox("Exchange", EXCHANGES, index=0)
        with f4:
            max_pe = st.slider("Max P/E Ratio", 5.0, 150.0, 80.0, step=5.0)

        # Run Screener
        with st.spinner("Filtering multi-exchange equity universe..."):
            results = screen_stocks(
                sector=sel_sector,
                country=sel_country,
                exchange=sel_exchange,
                max_pe=max_pe,
            )

        st.markdown(f"### Screened Assets ({len(results)} Matches)")
        if results:
            df_screen = pd.DataFrame([
                {
                    "Ticker": r["ticker"],
                    "Company Name": r["name"],
                    "Sector": r["sector"],
                    "Exchange": r["exchange"],
                    "Country": r["country"],
                    "Price": r["formatted_price"],
                    "Day Change": f"{r['change_pct']:+.2f}%",
                    "P/E Ratio": r["pe_ratio"],
                    "Profit Margin": f"{r['profit_margin_pct']}%" if r["profit_margin_pct"] != "N/A" else "N/A",
                    "Beta": r["beta"],
                }
                for r in results
            ])
            st.dataframe(df_screen, use_container_width=True, hide_index=True)
        else:
            st.info("No companies matched the current screening criteria. Try relaxing your filters.")

    with tab_compare:
        st.markdown("### Select Companies for Side-by-Side Analysis")
        compare_tickers = st.multiselect(
            "Choose 2 or more stocks to compare:",
            options=["NVDA", "AAPL", "MSFT", "TSLA", "RELIANCE.NS", "TCS.NS", "INFY.NS", "7203.T", "SIE.DE"],
            default=["NVDA", "AAPL", "MSFT"],
        )

        if len(compare_tickers) >= 2:
            with st.spinner("Generating side-by-side financial comparison..."):
                comp_data = compare_companies_side_by_side(compare_tickers)

            comp_df = pd.DataFrame(comp_data["comparison_table"])
            st.dataframe(comp_df, use_container_width=True, hide_index=True)
        else:
            st.info("Please select at least 2 companies to generate a side-by-side comparison.")
