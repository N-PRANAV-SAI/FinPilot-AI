"""FinBERT financial sentiment analysis using ProsusAI/finbert."""
import logging
import pandas as pd
from config.settings import settings

log = logging.getLogger(__name__)


class FinBERTAnalyzer:
    """Analyzes financial news sentiment using the ProsusAI/finbert model."""

    def __init__(self):
        self._pipe = None

    def _load(self):
        """Lazy-load the FinBERT pipeline."""
        if self._pipe is None:
            log.info("Loading FinBERT model: %s", settings.finbert_model)
            try:
                from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline
                try:
                    tokenizer = AutoTokenizer.from_pretrained(settings.finbert_model, local_files_only=True)
                    model = AutoModelForSequenceClassification.from_pretrained(settings.finbert_model, local_files_only=True)
                except Exception:
                    tokenizer = AutoTokenizer.from_pretrained(settings.finbert_model)
                    model = AutoModelForSequenceClassification.from_pretrained(settings.finbert_model)

                self._pipe = pipeline(
                    "text-classification",
                    model=model,
                    tokenizer=tokenizer,
                    top_k=None,
                    truncation=True,
                    max_length=512,
                )
                log.info("FinBERT model loaded successfully.")
            except Exception as exc:
                log.error("Failed to load FinBERT model: %s", exc)
                raise RuntimeError(
                    f"FinBERT model ({settings.finbert_model}) could not be loaded: {exc}. "
                    "Ensure transformers and torch are installed."
                ) from exc

    def analyze(self, news: list[dict]) -> pd.DataFrame:
        """Classify sentiment for a list of news items.
        
        Args:
            news: List of dicts with 'title' and optional 'text', 'published_at', 'url', 'source'.
            
        Returns:
            DataFrame with sentiment classification labels and probabilities.
        """
        if not news:
            return pd.DataFrame()

        self._load()

        # Combine title and text, truncate to avoid token limit
        texts = []
        for item in news:
            text = f"{item.get('title', '')}. {item.get('text', '')}".strip()
            texts.append(text[:1500])

        log.info("Running FinBERT sentiment inference on %d articles...", len(texts))
        raw_outputs = self._pipe(texts, batch_size=8)

        rows = []
        for item, scores in zip(news, raw_outputs):
            score_dict = {s["label"].lower(): float(s["score"]) for s in scores}
            label = max(score_dict, key=score_dict.get)
            rows.append({
                "title": item.get("title", ""),
                "text": item.get("text", ""),
                "published_at": item.get("published_at", ""),
                "url": item.get("url", ""),
                "source": item.get("source", ""),
                "positive": score_dict.get("positive", 0.0),
                "negative": score_dict.get("negative", 0.0),
                "neutral": score_dict.get("neutral", 0.0),
                "label": label,
            })

        df = pd.DataFrame(rows)
        log.info("FinBERT analysis completed for %d articles.", len(df))
        return df

    @staticmethod
    def summary(df: pd.DataFrame | None) -> dict:
        """Aggregate sentiment scores from classified news articles."""
        if df is None or df.empty:
            return {
                "available": False,
                "message": "No news or sentiment results available.",
            }

        n = len(df)
        pos_pct = float((df["label"] == "positive").mean() * 100)
        neg_pct = float((df["label"] == "negative").mean() * 100)
        neu_pct = float((df["label"] == "neutral").mean() * 100)
        avg_score = float((df["positive"] - df["negative"]).mean())

        if pos_pct > neg_pct and pos_pct > neu_pct:
            overall_label = "Positive"
        elif neg_pct > pos_pct and neg_pct > neu_pct:
            overall_label = "Negative"
        else:
            overall_label = "Neutral"

        return {
            "available": True,
            "count": n,
            "overall_label": overall_label,
            "positive_pct": pos_pct,
            "negative_pct": neg_pct,
            "neutral_pct": neu_pct,
            "score": avg_score,
        }

    @staticmethod
    def build_sentiment_features(sentiment_df: pd.DataFrame) -> dict:
        """Derive quantitative sentiment features for hybrid modeling."""
        if sentiment_df is None or sentiment_df.empty:
            return {}
        return {
            "sent_avg_positive": float(sentiment_df["positive"].mean()),
            "sent_avg_negative": float(sentiment_df["negative"].mean()),
            "sent_avg_neutral": float(sentiment_df["neutral"].mean()),
            "sent_score": float((sentiment_df["positive"] - sentiment_df["negative"]).mean()),
            "sent_positive_ratio": float((sentiment_df["label"] == "positive").mean()),
            "sent_negative_ratio": float((sentiment_df["label"] == "negative").mean()),
            "sent_count": len(sentiment_df),
        }
