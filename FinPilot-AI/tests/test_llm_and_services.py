"""Unit tests for LLM offline fallback, ticker validation, and SHAP explainability."""
import pytest
import numpy as np
import pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer

from backend.data.market_data import validate_ticker
from backend.data.news_data import fetch_news
from backend.llm.explanation_generator import _build_offline_synthesis, generate_explanation
from backend.explainability.shap_explainer import explain


def test_validate_ticker_valid():
    """Verify valid ticker normalization."""
    assert validate_ticker("nvda") == "NVDA"
    assert validate_ticker("  AAPL  ") == "AAPL"
    assert validate_ticker("BRK.B") == "BRK.B"


def test_validate_ticker_invalid():
    """Verify invalid tickers raise descriptive ValueError."""
    with pytest.raises(ValueError, match="Enter a valid stock ticker"):
        validate_ticker("")

    with pytest.raises(ValueError, match="Enter a valid stock ticker"):
        validate_ticker("   ")

    with pytest.raises(ValueError, match="Enter a valid stock ticker"):
        validate_ticker("NVDA$#@")


def test_offline_explanation_synthesis():
    """Verify that offline explanation generates structured markdown with all components."""
    prediction = {
        "direction": "Positive",
        "probability": 0.65,
        "selected_model": "Logistic Regression",
    }
    sentiment = {
        "available": True,
        "overall_label": "Positive",
        "score": 0.42,
        "positive_pct": 60.0,
        "negative_pct": 10.0,
    }
    shap_info = {
        "top_positive": [{"feature": "rsi14", "contribution": 0.12}],
        "top_negative": [{"feature": "volatility20", "contribution": -0.05}],
    }
    evidence = [
        {
            "text": "Revenue surged 206% year-over-year driven by accelerated computing demand.",
            "metadata": {
                "document_title": "10-K Annual Report",
                "filing_date": "2024-02-21",
                "page": 14,
            },
        }
    ]

    report = _build_offline_synthesis(
        ticker="NVDA",
        prediction=prediction,
        sentiment=sentiment,
        evidence=evidence,
        shap_info=shap_info,
        cause=RuntimeError("GEMINI_API_KEY is not configured"),
    )

    assert "NVDA" in report
    assert "Positive" in report
    assert "65.0%" in report
    assert "rsi14" in report
    assert "10-K Annual Report" in report
    assert "Educational Disclaimer" in report


def test_shap_explainer_with_logistic_regression():
    """Verify SHAP LinearExplainer correctly attributes features for a pipeline."""
    X_bg = pd.DataFrame({
        "feat_a": np.linspace(1, 10, 20),
        "feat_b": np.linspace(10, 1, 20),
    })
    y = np.array([0] * 10 + [1] * 10)

    pipe = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
        ("model", LogisticRegression(random_state=42)),
    ])
    pipe.fit(X_bg, y)

    X_row = pd.DataFrame({"feat_a": [5.5], "feat_b": [5.5]})

    result = explain(
        model=pipe,
        X_background=X_bg,
        X_row=X_row,
        feature_names=["feat_a", "feat_b"],
    )

    assert "importances" in result
    assert "base_value" in result
    assert "top_positive" in result or "top_negative" in result
    assert len(result["importances"]) == 2
