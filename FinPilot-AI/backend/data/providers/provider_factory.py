"""Provider factory for instantiating the active financial data provider."""
import logging
from config.settings import settings
from backend.data.providers.base_provider import GlobalMarketDataProvider
from backend.data.providers.yfinance_provider import YFinanceProvider
from backend.data.providers.fmp_provider import FMPProvider
from backend.data.providers.eodhd_provider import EODHDProvider

log = logging.getLogger(__name__)

_PROVIDER_INSTANCE: GlobalMarketDataProvider | None = None


def get_market_data_provider() -> GlobalMarketDataProvider:
    """Return the active market data provider based on configuration."""
    global _PROVIDER_INSTANCE
    if _PROVIDER_INSTANCE is not None:
        return _PROVIDER_INSTANCE

    choice = (settings.market_data_provider or "auto").strip().lower()

    if choice == "fmp":
        fmp = FMPProvider()
        if fmp.is_available():
            _PROVIDER_INSTANCE = fmp
            log.info("Active market data provider: Financial Modeling Prep (FMP)")
            return _PROVIDER_INSTANCE

    if choice == "eodhd":
        eod = EODHDProvider()
        if eod.is_available():
            _PROVIDER_INSTANCE = eod
            log.info("Active market data provider: EODHD")
            return _PROVIDER_INSTANCE

    if choice == "yfinance":
        _PROVIDER_INSTANCE = YFinanceProvider()
        log.info("Active market data provider: Yahoo Finance (zero-config)")
        return _PROVIDER_INSTANCE

    # Auto mode: check keys, default to yfinance
    fmp = FMPProvider()
    if fmp.is_available():
        _PROVIDER_INSTANCE = fmp
        log.info("Auto-selected market data provider: Financial Modeling Prep (FMP)")
        return _PROVIDER_INSTANCE

    eod = EODHDProvider()
    if eod.is_available():
        _PROVIDER_INSTANCE = eod
        log.info("Auto-selected market data provider: EODHD")
        return _PROVIDER_INSTANCE

    _PROVIDER_INSTANCE = YFinanceProvider()
    log.info("Auto-selected market data provider: Yahoo Finance (Universal Global Coverage)")
    return _PROVIDER_INSTANCE
