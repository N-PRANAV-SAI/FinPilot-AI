"""Financial feature engineering for ML models."""
import numpy as np
import pandas as pd
import logging

log = logging.getLogger(__name__)

# Technical features used by ML models
TECHNICAL_FEATURES = [
    "daily_return", "weekly_return", "sma20_gap", "sma50_gap", "ema20_gap",
    "rsi14", "macd", "macd_signal", "macd_histogram",
    "volatility20", "momentum10", "volume_change", "bb_position",
    "bb_width", "obv_change", "atr_ratio",
]

# Fundamental features (only used when available)
FUNDAMENTAL_FEATURES = [
    "revenue_growth", "profit_margin", "eps", "debt_to_equity",
]

# All features combined
FEATURES = TECHNICAL_FEATURES + FUNDAMENTAL_FEATURES


def _rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Calculate Relative Strength Index."""
    delta = series.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def _atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """Calculate Average True Range."""
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.rolling(period).mean()


def build_features(df: pd.DataFrame, fundamentals: dict | None = None) -> pd.DataFrame:
    """Generate technical and fundamental features from OHLCV data.
    
    Features are computed from historically available data only.
    Fundamental features are set to NaN by default to avoid look-ahead bias.
    """
    x = df.copy()
    close = x["Close"].astype(float)
    high = x["High"].astype(float)
    low = x["Low"].astype(float)
    volume = x["Volume"].astype(float)

    # --- Returns ---
    x["daily_return"] = close.pct_change()
    x["weekly_return"] = close.pct_change(5)

    # --- Moving Average Gaps ---
    sma20 = close.rolling(20).mean()
    sma50 = close.rolling(50).mean()
    ema20 = close.ewm(span=20, adjust=False).mean()
    x["sma20_gap"] = close / sma20 - 1
    x["sma50_gap"] = close / sma50 - 1
    x["ema20_gap"] = close / ema20 - 1

    # Store moving averages for charting (not used as ML features directly)
    x["SMA20"] = sma20
    x["SMA50"] = sma50
    x["EMA20"] = ema20

    # --- RSI ---
    x["rsi14"] = _rsi(close)

    # --- MACD ---
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    x["macd"] = ema12 - ema26
    x["macd_signal"] = x["macd"].ewm(span=9, adjust=False).mean()
    x["macd_histogram"] = x["macd"] - x["macd_signal"]

    # --- Volatility ---
    x["volatility20"] = x["daily_return"].rolling(20).std() * np.sqrt(252)

    # --- Momentum ---
    x["momentum10"] = close / close.shift(10) - 1

    # --- Volume Change ---
    x["volume_change"] = volume.pct_change().replace([np.inf, -np.inf], np.nan)

    # --- Bollinger Bands ---
    bb_mid = close.rolling(20).mean()
    bb_std = close.rolling(20).std()
    bb_upper = bb_mid + 2 * bb_std
    bb_lower = bb_mid - 2 * bb_std
    bb_range = bb_upper - bb_lower
    x["bb_position"] = (close - bb_lower) / bb_range.replace(0, np.nan)
    x["bb_width"] = bb_range / bb_mid.replace(0, np.nan)
    x["BB_Upper"] = bb_upper
    x["BB_Lower"] = bb_lower

    # --- OBV Change ---
    obv = (np.sign(close.diff()) * volume).cumsum()
    x["obv_change"] = obv.pct_change(5).replace([np.inf, -np.inf], np.nan)

    # --- ATR Ratio ---
    atr = _atr(high, low, close)
    x["atr_ratio"] = atr / close.replace(0, np.nan)

    # --- Fundamental features ---
    # Set to NaN to avoid look-ahead bias — current fundamentals should NOT
    # be applied to historical rows since point-in-time data is unavailable.
    for c in FUNDAMENTAL_FEATURES:
        x[c] = np.nan

    x = x.replace([np.inf, -np.inf], np.nan)
    log.info("Built %d features for %d rows", len(FEATURES), len(x))
    return x


def add_forward_target(features: pd.DataFrame, horizon: int = 5) -> pd.DataFrame:
    """Add binary forward-return target for classification.
    
    Target = 1 if Close[t+horizon]/Close[t] - 1 > 0, else 0.
    Last `horizon` rows have NaN target (future unknown).
    """
    x = features.copy()
    future_return = x["Close"].shift(-horizon) / x["Close"] - 1
    x["target"] = (future_return > 0).astype("float")
    x.loc[future_return.isna(), "target"] = np.nan
    return x


def get_feature_columns(df: pd.DataFrame, include_sentiment: bool = False) -> list[str]:
    """Get the list of feature columns available in the DataFrame."""
    cols = [c for c in TECHNICAL_FEATURES if c in df.columns]
    for c in FUNDAMENTAL_FEATURES:
        if c in df.columns and not df[c].isna().all():
            cols.append(c)
    if include_sentiment:
        sent_cols = [c for c in df.columns if c.startswith("sent_")]
        cols += sent_cols
    return cols
