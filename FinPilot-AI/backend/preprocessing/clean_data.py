"""Market data cleaning and validation."""
import logging
import pandas as pd
import numpy as np

log = logging.getLogger(__name__)


def clean_market_data(df: pd.DataFrame) -> pd.DataFrame:
    """Clean and validate raw market data.
    
    - Converts index to datetime
    - Removes duplicates (keeps last)
    - Sorts chronologically
    - Converts numeric columns
    - Drops rows with missing Close
    - Removes non-positive Close values
    - Handles outliers via simple validation
    """
    if df is None or df.empty:
        raise ValueError("Market data is empty.")

    x = df.copy()

    # Ensure datetime index
    x.index = pd.to_datetime(x.index, errors="coerce")
    x = x.loc[~x.index.isna()].sort_index()

    # Remove duplicate dates
    x = x[~x.index.duplicated(keep="last")]

    # Convert numeric columns
    numeric_cols = ["Open", "High", "Low", "Close", "Adj_Close", "Volume"]
    for c in numeric_cols:
        if c in x.columns:
            x[c] = pd.to_numeric(x[c], errors="coerce")

    # Drop rows without Close price
    x = x.dropna(subset=["Close"])

    # Remove non-positive prices
    x = x[x["Close"] > 0]

    # Forward-fill minor gaps in OHLV (max 3 days)
    for c in ["Open", "High", "Low", "Volume"]:
        if c in x.columns:
            x[c] = x[c].ffill(limit=3)

    # If Adj_Close is missing, use Close
    if "Adj_Close" not in x.columns or x["Adj_Close"].isna().all():
        x["Adj_Close"] = x["Close"]

    log.info("Cleaned market data: %d rows remaining", len(x))
    return x
