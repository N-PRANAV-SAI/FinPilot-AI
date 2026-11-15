"""ML model training with chronological splits and validation-based selection."""
import os
import logging
import numpy as np
import pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier

from backend.preprocessing.feature_engineering import (
    FEATURES,
    TECHNICAL_FEATURES,
    add_forward_target,
    get_feature_columns,
)
from backend.ml.evaluate import evaluate_model
from backend.ml.model_registry import save_model
from config.settings import settings

log = logging.getLogger(__name__)


def _build_model_zoo() -> dict:
    """Create the candidate model pipelines."""
    models = {
        "Logistic Regression": Pipeline([
            ("imputer", SimpleImputer(strategy="median", add_indicator=True)),
            ("scale", StandardScaler()),
            ("model", LogisticRegression(max_iter=1500, class_weight="balanced", random_state=42)),
        ]),
        "Random Forest": Pipeline([
            ("imputer", SimpleImputer(strategy="median", add_indicator=True)),
            ("model", RandomForestClassifier(
                n_estimators=300,
                min_samples_leaf=5,
                class_weight="balanced_subsample",
                random_state=42,
                n_jobs=-1,
            )),
        ]),
    }
    try:
        from xgboost import XGBClassifier
        models["XGBoost"] = Pipeline([
            ("imputer", SimpleImputer(strategy="median", add_indicator=True)),
            ("model", XGBClassifier(
                n_estimators=250,
                max_depth=3,
                learning_rate=0.03,
                subsample=0.85,
                colsample_bytree=0.85,
                eval_metric="logloss",
                random_state=42,
                n_jobs=4,
            )),
        ])
    except Exception as e:
        log.info("XGBoost not available or failed to import (%s); using scikit-learn models.", e)
    return models


def _chronological_split(data: pd.DataFrame, train_ratio: float = 0.65, val_ratio: float = 0.15):
    """Split data strictly chronologically into train, validation, and test sets.
    
    No random shuffling is applied to prevent lookahead data leakage in time series.
    """
    n = len(data)
    train_end = int(n * train_ratio)
    val_end = int(n * (train_ratio + val_ratio))
    return data.iloc[:train_end], data.iloc[train_end:val_end], data.iloc[val_end:]


def train_and_compare(
    feature_df: pd.DataFrame,
    ticker: str,
    sentiment_features: pd.DataFrame | None = None,
    include_sentiment: bool = False,
) -> dict:
    """Train multiple models, select best by validation ROC-AUC, evaluate on test.
    
    Args:
        feature_df: DataFrame with technical/fundamental features
        ticker: Company ticker
        sentiment_features: Optional DataFrame with FinBERT sentiment features
        include_sentiment: Whether to include sentiment features (hybrid mode)
        
    Returns:
        Dictionary containing fitted model, results, feature names, and metadata.
    """
    data = feature_df.copy()

    # Merge sentiment features if provided
    if sentiment_features is not None and not sentiment_features.empty and include_sentiment:
        for col in sentiment_features.columns:
            if col.startswith("sent_"):
                data[col] = sentiment_features[col]

    # Select valid feature columns
    cols = get_feature_columns(data, include_sentiment=include_sentiment)
    cols = [c for c in cols if c in data.columns]

    # Add 5-day forward target and drop unobservable rows
    data = add_forward_target(data, settings.prediction_horizon)
    data = data.dropna(subset=["target"])
    data = data.replace([np.inf, -np.inf], np.nan)

    n = len(data)
    if n < settings.min_training_rows:
        raise ValueError(
            f"Need at least {settings.min_training_rows} labelled observations for {ticker}; found {n}."
        )

    # Strictly chronological split
    train, val, test = _chronological_split(data, settings.train_ratio, settings.val_ratio)

    X_train, y_train = train[cols], train["target"].astype(int)
    X_val, y_val = val[cols], val["target"].astype(int)
    X_test, y_test = test[cols], test["target"].astype(int)

    if y_train.nunique() < 2 or y_val.nunique() < 2:
        raise ValueError("Chronological training/validation split contains only one class.")

    results = {}
    fitted = {}
    models = _build_model_zoo()

    for name, pipeline in models.items():
        log.info("Training %s for %s on %d rows...", name, ticker, len(X_train))
        try:
            pipeline.fit(X_train, y_train)
            metrics = evaluate_model(pipeline, X_val, y_val)
            results[name] = {"validation": metrics}
            fitted[name] = pipeline
            log.info("%s validation ROC-AUC: %.4f", name, metrics["roc_auc"])
        except Exception as exc:
            log.warning("Training %s failed: %s", name, exc)
            results[name] = {"validation": {"roc_auc": float("nan"), "error": str(exc)}}

    # Select best model strictly using validation metric
    valid_models = {
        k: v for k, v in results.items()
        if k in fitted and np.isfinite(v["validation"].get("roc_auc", float("nan")))
    }
    if not valid_models:
        raise ValueError("All candidate models failed during training.")

    selected = max(valid_models, key=lambda k: valid_models[k]["validation"]["roc_auc"])
    log.info("Selected best model: %s (val ROC-AUC: %.4f)", selected, results[selected]["validation"]["roc_auc"])

    # Refit selected model on train + validation combined, then evaluate ONCE on held-out test
    final_model = fitted[selected]
    combined_X = pd.concat([X_train, X_val])
    combined_y = pd.concat([y_train, y_val])
    final_model.fit(combined_X, combined_y)

    test_metrics = evaluate_model(final_model, X_test, y_test)
    results[selected]["test"] = test_metrics
    log.info("%s held-out test ROC-AUC: %.4f", selected, test_metrics["roc_auc"])

    # Also evaluate all other models on test for comparison display
    for name, pipeline in fitted.items():
        if name != selected:
            try:
                pipeline.fit(combined_X, combined_y)
                results[name]["test"] = evaluate_model(pipeline, X_test, y_test)
            except Exception:
                pass

    # Save model artifact
    bundle = {
        "model": final_model,
        "features": cols,
        "selected_model": selected,
        "horizon": settings.prediction_horizon,
        "ticker": ticker,
        "is_hybrid": include_sentiment,
    }
    path = save_model(bundle, f"{ticker}_{'hybrid' if include_sentiment else 'quant'}")

    return {
        "model": final_model,
        "selected_model": selected,
        "features": cols,
        "results": results,
        "train_size": len(train),
        "val_size": len(val),
        "test_size": len(test),
        "model_path": path,
        "validation_selected_metric": "ROC-AUC",
        "is_hybrid": include_sentiment,
        "last_train_date": str(train.index[-1].date()) if hasattr(train.index[-1], "date") else str(train.index[-1]),
        "last_val_date": str(val.index[-1].date()) if hasattr(val.index[-1], "date") else str(val.index[-1]),
        "test_start_date": str(test.index[0].date()) if hasattr(test.index[0], "date") else str(test.index[0]),
        "test_end_date": str(test.index[-1].date()) if hasattr(test.index[-1], "date") else str(test.index[-1]),
    }
