"""Dedicated Universal Global Company Search Engine Page for FinPilot AI."""
import streamlit as st
from backend.data.company_search import search_companies
from backend.data.global_exchanges import GLOBAL_EXCHANGES


def render_search_page():
    """Render universal search engine across 22+ global exchanges."""
    st.markdown("""
        <div style="margin-bottom: 1.5rem;">
            <div style="font-size: 0.85rem; font-weight: 700; color: #38bdf8; text-transform: uppercase; letter-spacing: 1px;">
                Universal Discovery Engine
            </div>
            <h1 style="margin: 0.2rem 0; font-size: 2.2rem; font-weight: 800; color: #f8fafc;">
                Global Company Search
            </h1>
            <p style="color: #94a3b8; font-size: 0.95rem;">
                Search across all publicly listed global companies by company name, ticker, exchange, or country.
            </p>
        </div>
    """, unsafe_allow_html=True)

    c_search, c_filter = st.columns([2.5, 1])
    with c_search:
        query = st.text_input("Enter Company Name, Symbol, or Keyword:", placeholder="e.g. Reliance, Siemens, Apple, Toyota, Samsung, HSBC")
    with c_filter:
        country_options = ["All Countries", "United States", "India", "Germany", "United Kingdom", "Japan", "South Korea", "Hong Kong", "China", "Australia"]
        selected_country = st.selectbox("Filter by Country:", country_options)

    country_filter = None if selected_country == "All Countries" else selected_country

    if not query:
        st.info("💡 Type any global company name above or search by ticker symbol. FinPilot AI dynamically resolves the primary exchange, currency code, and market provider.")
        
        # Benchmark Pills
        st.markdown("##### 🌐 Popular International Assets:")
        b_cols = st.columns(5)
        benchmarks = [
            ("RELIANCE.NS", "Reliance Industries (NSE)", "India", "₹"),
            ("NVDA", "NVIDIA Corp (NASDAQ)", "United States", "$"),
            ("7203.T", "Toyota Motor (TSE)", "Japan", "¥"),
            ("SIE.DE", "Siemens AG (XETRA)", "Germany", "€"),
            ("005930.KS", "Samsung (KRX)", "South Korea", "₩")
        ]
        for idx, (t, n, c, s) in enumerate(benchmarks):
            with b_cols[idx]:
                if st.button(f"{t}\n{n}", key=f"bench_{t}", use_container_width=True):
                    st.session_state["selected_ticker"] = t
                    st.session_state["nav"] = "Company Analysis"
                    st.rerun()
        return

    # Execute Search
    with st.spinner(f"Searching global markets for '{query}'..."):
        results = search_companies(query, country_filter=country_filter)

    if not results:
        st.warning(f"No company matches found for '{query}' in {selected_country}. Verify the company spelling or try searching without a country filter.")
        return

    st.markdown(f"#### Found {len(results)} Matching Companies:")
    
    for r in results:
        with st.container():
            flag = r.get("flag", "🌐")
            st.markdown(f"""
                <div style="background: #0f172a; border: 1px solid #1e293b; border-radius: 12px; padding: 18px; margin-bottom: 12px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
                        <div>
                            <span style="font-size: 1.4rem; margin-right: 8px;">{flag}</span>
                            <span style="font-size: 1.25rem; font-weight: 700; color: #f8fafc;">{r['name']}</span>
                            <span style="background: #1e293b; color: #38bdf8; padding: 2px 8px; border-radius: 6px; font-weight: 700; margin-left: 8px;">
                                {r['ticker']}
                            </span>
                            <div style="color: #94a3b8; font-size: 0.85rem; margin-top: 4px;">
                                Exchange: <b>{r['exchange']}</b> &nbsp;|&nbsp; 
                                Country: <b>{r['country']}</b> &nbsp;|&nbsp; 
                                Currency: <b>{r['currency']} ({r['currency_symbol']})</b> &nbsp;|&nbsp; 
                                Type: <b>{r.get('type', 'Equity')}</b>
                            </div>
                        </div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

            a_col1, a_col2, a_col3 = st.columns([1, 1, 3])
            with a_col1:
                if st.button("📊 Analyze Company", key=f"an_{r['ticker']}", use_container_width=True):
                    st.session_state["selected_ticker"] = r["ticker"]
                    st.session_state["nav"] = "Company Analysis"
                    st.rerun()
            with a_col2:
                if st.button("🟢 Trade Virtually", key=f"tr_{r['ticker']}", use_container_width=True):
                    st.session_state["active_ticker"] = r["ticker"]
                    st.session_state["nav"] = "Virtual Investing"
                    st.rerun()
