"""Unit tests for market data cleaning and validation."""
import pandas as pd
import numpy as np
import pytest
from backend.preprocessing.clean_data import clean_market_data


def test_clean_market_data_sorts_and_deduplicates():
    """Verify that market data is strictly chronological and deduplicated."""
    idx = pd.to_datetime(["2024-01-03", "2024-01-01", "2024-01-02", "2024-01-01"])
    df = pd.DataFrame({
        "Open": [102.0, 100.0, 101.0, 99.0],
        "High": [103.0, 101.0, 102.0, 100.0],
        "Low": [101.0, 99.0, 100.0, 98.0],
        "Close": [102.5, 100.5, 101.5, 99.5],
        "Adj_Close": [102.5, 100.5, 101.5, 99.5],
        "Volume": [1000, 1000, 1000, 1000],
    }, index=idx)

    cleaned = clean_market_data(df)
    assert cleaned.index.is_monotonic_increasing
    assert len(cleaned) == 3
    # Check that keep='last' preserved the last duplicate
    assert cleaned.loc["2024-01-01", "Close"] == 99.5


def test_clean_market_data_removes_invalid_prices():
    """Verify that non-positive close prices and nulls are dropped."""
    idx = pd.date_range("2024-01-01", periods=4)
    df = pd.DataFrame({
        "Open": [10.0, 10.0, 10.0, 10.0],
        "High": [12.0, 12.0, 12.0, 12.0],
        "Low": [9.0, 9.0, 9.0, 9.0],
        "Close": [10.0, -5.0, np.nan, 11.0],
        "Volume": [500, 500, 500, 500],
    }, index=idx)

    cleaned = clean_market_data(df)
    assert len(cleaned) == 2
    assert (cleaned["Close"] > 0).all()


def test_clean_market_data_empty_raises_error():
    """Verify that empty data raises a descriptive ValueError."""
    with pytest.raises(ValueError, match="Market data is empty"):
        clean_market_data(pd.DataFrame())
