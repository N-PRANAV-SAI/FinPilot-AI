"""Unit tests for feature engineering and forward target generation."""
import numpy as np
import pandas as pd
import pytest
from backend.preprocessing.feature_engineering import (
    build_features,
    add_forward_target,
    FEATURES,
    TECHNICAL_FEATURES,
)


def test_build_features_computes_technical_indicators():
    """Verify that moving average gaps, RSI, MACD, and Bollinger Bands are computed."""
    dates = pd.date_range("2023-01-01", periods=120)
    # Generate synthetic price series with upward drift
    np.random.seed(42)
    prices = 100.0 + np.cumsum(np.random.randn(120) + 0.1)

    df = pd.DataFrame({
        "Open": prices - 0.5,
        "High": prices + 1.0,
        "Low": prices - 1.0,
        "Close": prices,
        "Adj_Close": prices,
        "Volume": np.random.randint(10000, 50000, size=120),
    }, index=dates)

    feat_df = build_features(df)

    # Check key columns exist
    for col in ["daily_return", "weekly_return", "sma20_gap", "rsi14", "macd", "volatility20", "bb_position"]:
        assert col in feat_df.columns, f"Missing feature: {col}"

    # Verify RSI is bounded in [0, 100]
    valid_rsi = feat_df["rsi14"].dropna()
    assert (valid_rsi >= 0).all() and (valid_rsi <= 100).all()

    # Verify volatility is strictly non-negative
    valid_vol = feat_df["volatility20"].dropna()
    assert (valid_vol >= 0).all()


def test_add_forward_target_alignment():
    """Verify forward target alignment and absence of lookahead on last horizon rows."""
    dates = pd.date_range("2023-01-01", periods=30)
    # Strictly monotonically increasing prices
    prices = np.arange(30, dtype=float) + 50.0

    df = pd.DataFrame({
        "Open": prices,
        "High": prices + 1,
        "Low": prices - 1,
        "Close": prices,
        "Volume": 1000.0,
    }, index=dates)

    target_df = add_forward_target(df, horizon=5)

    assert "target" in target_df.columns

    # First row: price goes up by 5 days -> target should be 1
    assert target_df["target"].iloc[0] == 1.0

    # Exactly the last 5 rows must have NaN target because their future return is unobservable
    assert target_df["target"].iloc[-5:].isna().all()
    assert target_df["target"].iloc[:-5].notna().all()


def test_fundamental_features_are_nan_to_prevent_lookahead():
    """Verify that current fundamental ratios are not backfilled into historical training rows."""
    dates = pd.date_range("2023-01-01", periods=20)
    df = pd.DataFrame({
        "Open": 10.0, "High": 11.0, "Low": 9.0, "Close": 10.0, "Volume": 1000.0,
    }, index=dates)

    feat_df = build_features(df, fundamentals={"profit_margin": 0.25})
    for f in ["revenue_growth", "profit_margin", "eps", "debt_to_equity"]:
        assert feat_df[f].isna().all(), f"Fundamental feature {f} should be NaN in historical rows"
