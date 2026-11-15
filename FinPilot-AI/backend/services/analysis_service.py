"""Central orchestration service for FinPilot AI global financial analysis."""
import logging
from datetime import datetime, timezone
import pandas as pd
import numpy as np

from backend.data.market_data import fetch_market_data, get_latest_price
from backend.data.financial_data import fetch_fundamentals
from backend.data.news_data import fetch_news
from backend.data.filings_data import discover_company_documents
from backend.data.global_exchanges import get_exchange_info
from backend.preprocessing.clean_data import clean_market_data
from backend.preprocessing.feature_engineering import build_features
from backend.ml.train import train_and_compare
from backend.ml.predict import predict_latest
from backend.sentiment.finbert_analyzer import FinBERTAnalyzer
from backend.explainability.shap_explainer import explain
from backend.rag.retriever import FinancialRetriever
from backend.llm.explanation_generator import generate_explanation
from database.db import SessionLocal
from database.models import (
    Company,
    MarketData as MarketDataModel,
    Prediction as PredictionModel,
    ModelMetrics as ModelMetricsModel,
    SentimentAnalysis as SentimentAnalysisModel,
    AnalysisHistory as AnalysisHistoryModel,
)

log = logging.getLogger(__name__)


def run_full_analysis(ticker: str, period: str = "5y", run_llm: bool = True) -> dict:
    """Run an end-to-end financial analysis for any global stock ticker.
    
    Orchestrates:
    1. Historical market data ingestion & cleaning
    2. Fundamental metrics extraction (reporting currency, sector, statements)
    3. Technical & fundamental feature engineering
    4. Machine Learning model training & chronological validation/testing
    5. Quantitative-only vs Hybrid model comparison (Approach A vs Approach B)
    6. Real-time directional prediction for next 5 exchange trading sessions
    7. FinBERT financial news sentiment analysis
    8. SHAP explainability for the selected model
    9. Global regulatory filing discovery (SEC EDGAR, International Disclosures)
    10. Evidence-grounded LLM synthesis via Gemini (if configured)
    11. SQLite database persistence with international metadata
    
    Returns:
        Structured dictionary containing all computed artifacts.
    """
    ticker = ticker.strip().upper()
    log.info("Starting global financial analysis for %s (window: %s)...", ticker, period)

    # 1. Fetch Fundamentals First to discover company name, country, exchange & currency
    fundamentals = fetch_fundamentals(ticker)
    company_name = fundamentals.get("company_name", ticker)
    exc_info = get_exchange_info(fundamentals.get("exchange") or ticker)
    country = fundamentals.get("country") or exc_info.country
    exchange = fundamentals.get("exchange") or exc_info.code
    currency = fundamentals.get("currency") or exc_info.currency
    currency_symbol = fundamentals.get("currency_symbol") or exc_info.currency_symbol

    # 2. Fetch & Clean Historical Market Data
    raw_market = fetch_market_data(ticker, period=period)
    clean_market = clean_market_data(raw_market)
    latest_price = get_latest_price(clean_market, currency=currency)

    # 3. Feature Engineering
    features = build_features(clean_market, fundamentals)

    # 4. News Collection & FinBERT Sentiment Analysis
    news = fetch_news(ticker, company_name=company_name, exchange=exchange, days=21)
    sentiment_df = None
    sentiment_summary = {
        "available": False,
        "message": "No news articles found or news provider API key not configured.",
    }
    sentiment_features_df = None

    if news:
        try:
            analyzer = FinBERTAnalyzer()
            sentiment_df = analyzer.analyze(news)
            sentiment_summary = FinBERTAnalyzer.summary(sentiment_df)
            sent_feats = FinBERTAnalyzer.build_sentiment_features(sentiment_df)

            # Build a time-indexed sentiment feature DataFrame
            if sent_feats:
                sentiment_features_df = pd.DataFrame(
                    [sent_feats] * len(features),
                    index=features.index,
                )
        except Exception as exc:
            log.warning("FinBERT sentiment analysis unavailable: %s", exc)
            sentiment_summary = {
                "available": False,
                "message": f"FinBERT unavailable: {exc}. Install transformers and torch to enable.",
            }

    # 5. Train Quantitative-Only Models (Approach A)
    log.info("Training Approach A (Quantitative-only models) for %s...", ticker)
    quant_training = train_and_compare(
        feature_df=features,
        ticker=ticker,
        include_sentiment=False,
    )

    # 6. Train Hybrid Models (Approach B) if sentiment is available
    hybrid_training = None
    if sentiment_features_df is not None and sentiment_summary.get("available"):
        try:
            log.info("Training Approach B (Hybrid Quantitative + FinBERT models) for %s...", ticker)
            hybrid_training = train_and_compare(
                feature_df=features,
                ticker=ticker,
                sentiment_features=sentiment_features_df,
                include_sentiment=True,
            )
        except Exception as exc:
            log.warning("Hybrid model training skipped: %s", exc)

    # 7. Generate Real-time Prediction using Best Quantitative Model
    prediction = predict_latest(quant_training, features)
    prediction["exchange"] = exchange
    prediction["currency"] = currency

    # 8. Compute SHAP Explainability on Demand
    shap_info = None
    try:
        model = quant_training["model"]
        feature_cols = quant_training["features"]
        clean_features = features.reindex(columns=feature_cols).dropna(subset=[feature_cols[0]])

        bg_sample = clean_features.iloc[-80:-1].fillna(clean_features.median(numeric_only=True))
        row_instance = clean_features.tail(1).fillna(clean_features.median(numeric_only=True))

        shap_info = explain(
            model=model,
            X_background=bg_sample,
            X_row=row_instance,
            feature_names=feature_cols,
        )
    except Exception as exc:
        log.warning("SHAP calculation skipped or failed: %s", exc)

    # 9. Discover Regulatory Filings & Disclosures
    filings = []
    try:
        filings = discover_company_documents(
            ticker=ticker,
            company_name=company_name,
            country=country,
            exchange=exchange,
            limit=8,
        )
    except Exception as exc:
        log.warning("Filing discovery failed for %s: %s", ticker, exc)

    # 10. Generate Evidence-Grounded LLM Explanation
    llm_explanation = None
    if run_llm:
        try:
            retriever = FinancialRetriever()
            retrieved_evidence = retriever.retrieve(
                question=f"Key business risks, revenue performance, and financial outlook for {company_name}",
                ticker=ticker,
                k=4,
            )
            llm_explanation = generate_explanation(
                ticker=ticker,
                prediction=prediction,
                sentiment=sentiment_summary,
                evidence=retrieved_evidence,
                shap_info=shap_info or {},
                fundamentals=fundamentals,
                market_summary=latest_price,
            )
        except Exception as exc:
            log.warning("LLM explanation generation deferred: %s", exc)
            llm_explanation = f"LLM generation notice: {exc}"

    # 11. Database Persistence
    _persist_analysis(
        ticker=ticker,
        company_name=company_name,
        country=country,
        exchange=exchange,
        currency=currency,
        fundamentals=fundamentals,
        clean_market=clean_market,
        prediction=prediction,
        quant_training=quant_training,
        hybrid_training=hybrid_training,
        sentiment_df=sentiment_df,
        sentiment_summary=sentiment_summary,
        llm_explanation=llm_explanation,
    )

    last_market_date = str(clean_market.index[-1].date()) if hasattr(clean_market.index[-1], "date") else str(clean_market.index[-1])

    return {
        "ticker": ticker,
        "company_name": company_name,
        "country": country,
        "exchange": exchange,
        "currency": currency,
        "currency_symbol": currency_symbol,
        "flag": exc_info.flag,
        "market": clean_market,
        "latest_price": latest_price,
        "fundamentals": fundamentals,
        "features": features,
        "training": quant_training,
        "hybrid_training": hybrid_training,
        "prediction": prediction,
        "news": news,
        "sentiment_df": sentiment_df,
        "sentiment": sentiment_summary,
        "shap_info": shap_info,
        "sec_filings": filings,
        "filings": filings,
        "llm_explanation": llm_explanation,
        "last_market_date": last_market_date,
    }


def _persist_analysis(
    ticker: str,
    company_name: str,
    country: str,
    exchange: str,
    currency: str,
    fundamentals: dict,
    clean_market: pd.DataFrame,
    prediction: dict,
    quant_training: dict,
    hybrid_training: dict | None,
    sentiment_df: pd.DataFrame | None,
    sentiment_summary: dict,
    llm_explanation: str | None,
):
    """Persist global analysis results to SQLite database."""
    db = SessionLocal()
    try:
        # Upsert Company
        company = db.query(Company).filter(Company.ticker == ticker).first()
        if not company:
            company = Company(
                company_name=company_name,
                ticker=ticker,
                sector=fundamentals.get("sector"),
                industry=fundamentals.get("industry"),
                country=country,
                exchange=exchange,
                currency=currency,
            )
            db.add(company)
        else:
            company.company_name = company_name
            company.country = country
            company.exchange = exchange
            company.currency = currency

        # Record Prediction
        pred_record = PredictionModel(
            ticker=ticker,
            prediction_horizon=prediction.get("horizon_trading_days", 5),
            predicted_class=prediction.get("predicted_class"),
            predicted_probability=prediction.get("probability"),
            selected_model=quant_training.get("selected_model"),
            exchange=exchange,
            currency=currency,
        )
        db.add(pred_record)

        # Record Model Metrics for Quantitative Models
        for model_name, metrics_dict in quant_training.get("results", {}).items():
            val = metrics_dict.get("validation", {})
            test = metrics_dict.get("test", {})
            if val and "roc_auc" in val and np.isfinite(val.get("roc_auc", float("nan"))):
                db.add(ModelMetricsModel(
                    model_name=f"{model_name} (Quant)",
                    ticker=ticker,
                    accuracy=val.get("accuracy"),
                    precision=val.get("precision"),
                    recall=val.get("recall"),
                    f1_score=val.get("f1"),
                    roc_auc=val.get("roc_auc"),
                    dataset_type="quantitative",
                ))

        # Record Model Metrics for Hybrid Models if available
        if hybrid_training:
            for model_name, metrics_dict in hybrid_training.get("results", {}).items():
                val = metrics_dict.get("validation", {})
                if val and "roc_auc" in val and np.isfinite(val.get("roc_auc", float("nan"))):
                    db.add(ModelMetricsModel(
                        model_name=f"{model_name} (Hybrid)",
                        ticker=ticker,
                        accuracy=val.get("accuracy"),
                        precision=val.get("precision"),
                        recall=val.get("recall"),
                        f1_score=val.get("f1"),
                        roc_auc=val.get("roc_auc"),
                        dataset_type="hybrid",
                    ))

        # Record Sentiment Analysis samples
        if sentiment_df is not None and not sentiment_df.empty:
            for _, row in sentiment_df.head(15).iterrows():
                db.add(SentimentAnalysisModel(
                    ticker=ticker,
                    news_title=str(row.get("title", ""))[:400],
                    sentiment_label=str(row.get("label", "")),
                    positive_score=float(row.get("positive", 0.0)),
                    negative_score=float(row.get("negative", 0.0)),
                    neutral_score=float(row.get("neutral", 0.0)),
                    source_url=str(row.get("url", "")),
                ))

        # Record Overall Analysis History
        pred_text = f"{prediction.get('direction')} ({prediction.get('probability', 0.0):.1%} prob, {quant_training.get('selected_model')})"
        sent_text = (
            f"Overall: {sentiment_summary.get('overall_label', 'N/A')} "
            f"(Score: {sentiment_summary.get('score', 0.0):.2f}, "
            f"+{sentiment_summary.get('positive_pct', 0.0):.0f}%/-{sentiment_summary.get('negative_pct', 0.0):.0f}%)"
            if sentiment_summary.get("available")
            else "Sentiment not available"
        )

        db.add(AnalysisHistoryModel(
            ticker=ticker,
            company_name=company_name,
            country=country,
            exchange=exchange,
            currency=currency,
            prediction_summary=pred_text,
            sentiment_summary=sent_text,
            selected_model=quant_training.get("selected_model"),
            llm_explanation=llm_explanation or "Not generated yet.",
        ))

        db.commit()
        log.info("Analysis history and metrics committed to database for %s (%s).", ticker, country)
    except Exception as exc:
        db.rollback()
        log.error("Failed to persist analysis to database: %s", exc)
    finally:
        db.close()
