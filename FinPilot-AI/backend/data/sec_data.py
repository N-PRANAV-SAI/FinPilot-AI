"""Regulatory filings data retrieval router."""
from backend.data.filings_data import discover_company_documents, fetch_recent_filings, _get_sec_ticker_map

ticker_map = _get_sec_ticker_map

__all__ = ["discover_company_documents", "fetch_recent_filings", "ticker_map"]
