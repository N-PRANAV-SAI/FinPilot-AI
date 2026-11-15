"""Unit tests for FinBERT sentiment aggregation logic."""
import pandas as pd
import pytest
from backend.sentiment.finbert_analyzer import FinBERTAnalyzer


def test_empty_sentiment_summary_returns_unavailable():
    """Verify that empty inputs gracefully indicate unavailability."""
    res_none = FinBERTAnalyzer.summary(None)
    assert res_none["available"] is False

    res_empty = FinBERTAnalyzer.summary(pd.DataFrame())
    assert res_empty["available"] is False


def test_sentiment_summary_aggregates_correctly():
    """Verify percentage calculations and overall score calculation."""
    df = pd.DataFrame([
        {"title": "Revenue Surges", "label": "positive", "positive": 0.9, "negative": 0.05, "neutral": 0.05},
        {"title": "Profits Beat Expectations", "label": "positive", "positive": 0.8, "negative": 0.1, "neutral": 0.1},
        {"title": "Market Remains Steady", "label": "neutral", "positive": 0.2, "negative": 0.1, "neutral": 0.7},
        {"title": "Lawsuit Filed Against Firm", "label": "negative", "positive": 0.05, "negative": 0.85, "neutral": 0.1},
    ])

    summary = FinBERTAnalyzer.summary(df)

    assert summary["available"] is True
    assert summary["count"] == 4
    assert summary["positive_pct"] == 50.0  # 2 of 4
    assert summary["negative_pct"] == 25.0  # 1 of 4
    assert summary["neutral_pct"] == 25.0   # 1 of 4
    assert summary["overall_label"] == "Positive"
    # Net score = Mean(positive - negative)
    # (0.9-0.05 + 0.8-0.1 + 0.2-0.1 + 0.05-0.85) / 4 = (0.85 + 0.7 + 0.1 - 0.8) / 4 = 0.85 / 4 = 0.2125
    assert pytest.approx(summary["score"], 0.001) == 0.2125


def test_build_sentiment_features_produces_model_features():
    """Verify sentiment feature dict generation for the hybrid model."""
    df = pd.DataFrame([
        {"positive": 0.8, "negative": 0.1, "neutral": 0.1, "label": "positive"},
        {"positive": 0.2, "negative": 0.6, "neutral": 0.2, "label": "negative"},
    ])

    feats = FinBERTAnalyzer.build_sentiment_features(df)
    assert "sent_avg_positive" in feats
    assert "sent_avg_negative" in feats
    assert "sent_score" in feats
    assert feats["sent_positive_ratio"] == 0.5
    assert feats["sent_count"] == 2
