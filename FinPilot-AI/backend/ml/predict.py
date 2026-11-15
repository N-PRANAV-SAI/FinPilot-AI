"""Generate real-time predictions using fitted model bundles."""
import logging
import numpy as np
import pandas as pd

log = logging.getLogger(__name__)


def predict_latest(bundle: dict, feature_df: pd.DataFrame) -> dict:
    """Generate a prediction for the latest available market observation.
    
    Args:
        bundle: Dictionary containing fitted model, feature column names, and metadata.
        feature_df: DataFrame containing computed technical and fundamental features.
        
    Returns:
        Dict with predicted_class, direction, class probabilities, and prediction horizon.
    """
    cols = bundle["features"]
    row = feature_df.reindex(columns=cols).tail(1)

    if row.empty or row.isna().all(axis=1).iloc[0]:
        raise ValueError("Latest feature observation is incomplete; cannot generate prediction.")

    model = bundle["model"]
    proba = model.predict_proba(row)[0]
    cls = int(np.argmax(proba))

    result = {
        "predicted_class": cls,
        "direction": "Positive" if cls == 1 else "Negative or Zero",
        "probability": float(proba[cls]),
        "positive_probability": float(proba[1]),
        "negative_probability": float(proba[0]),
        "horizon_trading_days": bundle.get("horizon", 5),
        "selected_model": bundle.get("selected_model", "Unknown"),
        "last_market_date": str(feature_df.index[-1].date()) if hasattr(feature_df.index[-1], "date") else str(feature_df.index[-1]),
    }

    log.info(
        "Prediction for %s: %s (confidence=%.1f%%, model=%s)",
        bundle.get("ticker", "asset"),
        result["direction"],
        result["probability"] * 100,
        result["selected_model"],
    )
    return result
