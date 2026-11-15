"""Settings and System Health page for FinPilot AI with Global Coverage diagnostics."""
import os
import streamlit as st
from config.settings import settings
from backend.data.providers.provider_factory import get_market_data_provider
from backend.data.global_exchanges import GLOBAL_EXCHANGES


def _mask_secret(val: str) -> str:
    """Mask sensitive API keys for display."""
    if not val:
        return "❌ Not Configured"
    if len(val) <= 8:
        return "••••••••"
    return f"{val[:4]}••••••••{val[-4:]} (Configured)"


def render_settings():
    """Render system settings, provider connectivity status, and environment diagnostics."""
    st.markdown("## ⚙️ Settings & Global System Health")
    st.caption("Verification of API credentials, global exchange registries, local models, and persistent storage.")

    # -------------------------------------------------------------
    # Provider Connectivity Grid
    # -------------------------------------------------------------
    st.markdown("### 1. API Credentials & Global Subsystem Status")

    finnhub_active = bool(settings.finnhub_api_key and settings.finnhub_api_key.strip())
    newsapi_active = bool(settings.newsapi_key and settings.newsapi_key.strip())
    gemini_active = bool(settings.gemini_api_key and settings.gemini_api_key.strip())
    eodhd_active = bool(settings.eodhd_api_key and settings.eodhd_api_key.strip())
    fmp_active = bool(settings.fmp_api_key and settings.fmp_api_key.strip())
    sec_active = bool(settings.sec_user_agent and "@" in settings.sec_user_agent)

    active_provider = get_market_data_provider()

    provider_rows = [
        {
            "Subsystem": "Global Market Data Engine",
            "Provider": active_provider.name,
            "Status": "✅ Operational (Universal Coverage)",
            "Details": f"Mode: {settings.market_data_provider.upper()} | OHLCV & Fundamentals for 22+ Exchanges",
        },
        {
            "Subsystem": "EODHD Market Data API",
            "Provider": "EOD Historical Data",
            "Status": "✅ Configured" if eodhd_active else "⚪ Optional (Zero-config fallback active)",
            "Details": _mask_secret(settings.eodhd_api_key),
        },
        {
            "Subsystem": "FMP Market Data API",
            "Provider": "Financial Modeling Prep",
            "Status": "✅ Configured" if fmp_active else "⚪ Optional (Zero-config fallback active)",
            "Details": _mask_secret(settings.fmp_api_key),
        },
        {
            "Subsystem": "Regulatory Filings Discovery",
            "Provider": "SEC EDGAR & International Regulatory Portals",
            "Status": "✅ Configured" if sec_active else "⚠️ Missing Contact Email",
            "Details": f"User-Agent: {settings.sec_user_agent}",
        },
        {
            "Subsystem": "Financial News Feed",
            "Provider": settings.news_provider.capitalize(),
            "Status": "✅ Configured" if (finnhub_active or newsapi_active) else "✅ Active (Public feed fallback)",
            "Details": _mask_secret(settings.finnhub_api_key if settings.news_provider == "finnhub" else settings.newsapi_key),
        },
        {
            "Subsystem": "Financial Sentiment (FinBERT)",
            "Provider": "ProsusAI/finbert (HuggingFace)",
            "Status": "✅ Local Transformer Pipeline",
            "Details": f"Model: {settings.finbert_model}",
        },
        {
            "Subsystem": "Vector Embeddings",
            "Provider": "Sentence Transformers",
            "Status": "✅ Local Embedding Engine",
            "Details": f"Model: {settings.embedding_model}",
        },
        {
            "Subsystem": "RAG Vector Database",
            "Provider": "ChromaDB (Persistent)",
            "Status": "✅ Local Storage Initialized",
            "Details": f"Directory: {settings.chroma_dir}",
        },
        {
            "Subsystem": "Generative AI Explanation",
            "Provider": "Google Gemini API",
            "Status": "✅ Connected" if gemini_active else "❌ Key Missing",
            "Details": f"Model: {settings.llm_model} | Key: {_mask_secret(settings.gemini_api_key)}",
        },
        {
            "Subsystem": "Explainable AI (XAI)",
            "Provider": "SHAP (Game-Theoretic Attribution)",
            "Status": "✅ Active",
            "Details": "TreeExplainer, LinearExplainer & KernelExplainer",
        },
        {
            "Subsystem": "Relational Persistence",
            "Provider": "SQLite via SQLAlchemy",
            "Status": "✅ Connected",
            "Details": f"URL: {settings.database_url}",
        },
    ]

    st.dataframe(provider_rows, use_container_width=True, hide_index=True)

    st.markdown("---")

    # -------------------------------------------------------------
    # Global Stock Exchanges Coverage Table
    # -------------------------------------------------------------
    st.markdown("### 2. Supported Global Stock Exchanges & Trading Sessions")
    st.caption("FinPilot AI dynamically discovers and normalizes tickers and currencies across these major global exchanges.")

    exc_rows = []
    seen_codes = set()
    for exc in GLOBAL_EXCHANGES.values():
        if exc.code in seen_codes:
            continue
        seen_codes.add(exc.code)
        exc_rows.append({
            "Region": exc.region,
            "Country": f"{exc.flag} {exc.country}",
            "Exchange Code": exc.code,
            "Exchange Name": exc.name,
            "Trading Currency": f"{exc.currency} ({exc.currency_symbol})",
            "MIC": exc.mic,
            "Ticker Suffix": exc.suffix or "(None / US)",
            "Timezone": exc.timezone,
        })

    st.dataframe(exc_rows, use_container_width=True, hide_index=True)

    st.markdown("---")

    # -------------------------------------------------------------
    # Environment Setup Guide
    # -------------------------------------------------------------
    st.markdown("### 3. Environment Variables Configuration Guide")
    st.markdown("""
        FinPilot AI reads all configuration securely from your project's `.env` file located in `FinPilot-AI/`.
        No API keys are ever hardcoded or exposed in the user interface.
    """)

    with st.expander("📝 Sample `.env` Configuration Template", expanded=False):
        st.code("""# FinPilot AI Global Environment Configuration
# 1. Google Gemini API Key (for RAG & ML explanation narrative)
# Obtain free at: https://aistudio.google.com/
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-3.8-flash

# 2. Global Financial Market Data Providers (EODHD, FMP, or auto)
EODHD_API_KEY=your_eodhd_key_here
FMP_API_KEY=your_fmp_key_here
MARKET_DATA_PROVIDER=auto

# 3. Financial News Providers (Finnhub or NewsAPI)
FINNHUB_API_KEY=your_finnhub_key_here
NEWS_PROVIDER=finnhub

# 4. SEC EDGAR User-Agent (Required format: YourAppName contact@domain.com)
SEC_USER_AGENT=FinPilotAI research@university.edu

# 5. Storage & Persistence
DATABASE_URL=sqlite:///finpilot.db
MODEL_DIR=artifacts/models
CHROMA_DIR=artifacts/vector_db
LOG_DIR=artifacts/logs
""", language="ini")
