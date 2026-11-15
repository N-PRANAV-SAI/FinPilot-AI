"""Unit tests for ML training, chronological splits, and prediction."""
import numpy as np
import pandas as pd
import pytest
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer

from backend.ml.predict import predict_latest
from backend.ml.evaluate import evaluate_model
from backend.ml.train import _chronological_split


def test_predict_latest_structure_and_bounds():
    """Verify that predict_latest returns bounded probabilities and required fields."""
    X = pd.DataFrame({
        "feat_a": [1.0, 2.0, 3.0, 4.0, 5.0],
        "feat_b": [0.1, 0.2, 0.3, 0.4, 0.5],
    }, index=pd.date_range("2024-01-01", periods=5))
    y = [0, 0, 1, 1, 1]

    pipe = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
        ("model", LogisticRegression()),
    ])
    pipe.fit(X, y)

    bundle = {
        "model": pipe,
        "features": ["feat_a", "feat_b"],
        "selected_model": "Logistic Regression",
        "horizon": 5,
        "ticker": "TEST",
    }

    pred = predict_latest(bundle, X)

    assert "predicted_class" in pred
    assert pred["predicted_class"] in (0, 1)
    assert pred["direction"] in ("Positive", "Negative or Zero")
    assert 0.0 <= pred["probability"] <= 1.0
    assert 0.0 <= pred["positive_probability"] <= 1.0
    assert 0.0 <= pred["negative_probability"] <= 1.0
    assert np.isclose(pred["positive_probability"] + pred["negative_probability"], 1.0)
    assert pred["horizon_trading_days"] == 5


def test_chronological_split_no_shuffle():
    """Verify that chronological splits maintain time ordering and do not overlap."""
    n = 200
    dates = pd.date_range("2020-01-01", periods=n)
    df = pd.DataFrame({"val": range(n)}, index=dates)

    train, val, test = _chronological_split(df, train_ratio=0.65, val_ratio=0.15)

    assert len(train) == 130
    assert len(val) == 30
    assert len(test) == 40
    assert len(train) + len(val) + len(test) == n

    # Strictly chronological
    assert train.index[-1] < val.index[0]
    assert val.index[-1] < test.index[0]


def test_evaluate_model_computes_all_metrics():
    """Verify evaluate_model returns standard binary classification metrics."""
    X = np.array([[0], [1], [2], [3], [4], [5]])
    y = np.array([0, 0, 0, 1, 1, 1])

    model = LogisticRegression().fit(X, y)
    metrics = evaluate_model(model, X, y)

    for key in ["accuracy", "precision", "recall", "f1", "roc_auc", "confusion_matrix"]:
        assert key in metrics, f"Missing metric {key}"

    assert 0.0 <= metrics["accuracy"] <= 1.0
    assert 0.0 <= metrics["roc_auc"] <= 1.0
    assert len(metrics["confusion_matrix"]) == 2
