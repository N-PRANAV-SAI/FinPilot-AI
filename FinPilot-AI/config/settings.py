"""Application settings loaded from environment variables and Streamlit secrets."""
from dataclasses import dataclass, field
import os
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env", override=True)
load_dotenv()


def _get_setting(key: str, default: str = "") -> str:
    """Retrieve setting from environment variable or Streamlit secrets with fallback."""
    val = os.getenv(key)
    if val:
        return val
    try:
        import streamlit as st
        if hasattr(st, "secrets") and key in st.secrets:
            return str(st.secrets[key])
    except Exception:
        pass
    return default


@dataclass(frozen=True)
class Settings:
    # API keys
    gemini_api_key: str = field(default_factory=lambda: _get_setting("GEMINI_API_KEY", ""))
    finnhub_api_key: str = field(default_factory=lambda: _get_setting("FINNHUB_API_KEY", ""))
    newsapi_key: str = field(default_factory=lambda: _get_setting("NEWSAPI_KEY", ""))
    eodhd_api_key: str = field(default_factory=lambda: _get_setting("EODHD_API_KEY", ""))
    fmp_api_key: str = field(default_factory=lambda: _get_setting("FMP_API_KEY", ""))
    sec_user_agent: str = field(default_factory=lambda: _get_setting("SEC_USER_AGENT", "FinPilotAI contact@example.com"))

    # Database
    database_url: str = field(default_factory=lambda: _get_setting("DATABASE_URL", f"sqlite:///{PROJECT_ROOT / 'finpilot.db'}"))

    # Artifact directories
    model_dir: str = field(default_factory=lambda: _get_setting("MODEL_DIR", str(PROJECT_ROOT / "artifacts" / "models")))
    chroma_dir: str = field(default_factory=lambda: _get_setting("CHROMA_DIR", str(PROJECT_ROOT / "artifacts" / "vector_db")))
    log_dir: str = field(default_factory=lambda: _get_setting("LOG_DIR", str(PROJECT_ROOT / "artifacts" / "logs")))
    chart_dir: str = field(default_factory=lambda: _get_setting("CHART_DIR", str(PROJECT_ROOT / "artifacts" / "charts")))

    # Model identifiers
    embedding_model: str = field(default_factory=lambda: _get_setting("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"))
    finbert_model: str = field(default_factory=lambda: _get_setting("FINBERT_MODEL", "ProsusAI/finbert"))
    llm_model: str = field(default_factory=lambda: _get_setting("GEMINI_MODEL", "gemini-3.8-flash"))

    # Provider selection
    market_data_provider: str = field(default_factory=lambda: _get_setting("MARKET_DATA_PROVIDER", "auto"))
    news_provider: str = field(default_factory=lambda: _get_setting("NEWS_PROVIDER", "finnhub"))

    # ML config
    prediction_horizon: int = 5
    min_training_rows: int = 180
    train_ratio: float = 0.65
    val_ratio: float = 0.15  # test = 1 - train - val = 0.20


settings = Settings()
