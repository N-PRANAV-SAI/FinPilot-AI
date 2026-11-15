# FinPilot AI — Global AI-Powered Financial Research & Virtual Investment Platform

[![Python 3.11](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/)
[![Streamlit Community Cloud](https://img.shields.io/badge/Streamlit-Community_Cloud-FF4B4B.svg)](https://streamlit.io/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688.svg)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Zero Real-Money Risk](https://img.shields.io/badge/Paper_Trading-100%25_Virtual-success.svg)](#paper-trading-architecture)

> **"Research Smarter. Practise Investing. Understand Your Money. Powered by FinPilot AI."**

FinPilot AI is an institutional-grade financial analytics and simulated investment platform. Inspired by the clean, intuitive onboarding of **Groww** and the deep technical charting of **TradingView**, it bridges the gap between complex quantitative research and accessible paper trading for retail investors, data scientists, and quantitative analysts.

All trading operations remain **100% simulated** with zero real-money connectivity.

---

## 📑 Table of Contents
1. [Core Features](#-core-features)
2. [Technology Stack](#-technology-stack)
3. [Architecture Overview](#-architecture-overview)
4. [Machine Learning & Forecasting Pipeline](#-machine-learning--forecasting-pipeline)
5. [Quantitative Research & Risk Analytics](#-quantitative-research--risk-analytics)
6. [Historical Backtesting Engine](#-historical-backtesting-engine)
7. [Streamlit Community Cloud Deployment](#-streamlit-community-cloud-deployment)
8. [Local Installation & Setup](#-local-installation--setup)
9. [Documentation Suite](#-documentation-suite)
10. [Limitations & Financial Disclaimers](#-limitations--financial-disclaimers)

---

## 🌟 Core Features

### 1. AI Profit Predictor & Scenario Engine
- **Return Magnitude Forecasting**: Walk-forward ensemble combining Random Forest Regressor and Ridge Regression with Student-t fat-tail intervals.
- **Three Concrete Scenarios**: Transparent **Bearish**, **Base (ML Median)**, and **Bullish** ending value projections.
- **Investment Goal Hurdle Simulator**: Rigorous mathematical compounding checks for ambitious targets (e.g. ₹10,000 to ₹1,00,000) across 1w, 2w, 1m, 3m, 6m, and 1y horizons. Honest statistical diagnosis of extreme hurdles.
- **Multi-Stock Markowitz Covariance**: Asset allocation modeling with Herfindahl-Hirschman (HHI) concentration metrics and maximum expected drawdown.

### 2. Quantitative Research Lab
- **Rolling Volatility**: 20-day and 60-day annualized rolling volatility bands.
- **Market Regression**: Beta, Jensen's Alpha, $R^2$, and correlation against benchmark indices (S&P 500, Nifty 50, DAX, NASDAQ).
- **Drawdown Profiling**: Running peak-to-trough drawdowns, Calmar ratios, and recovery timelines.
- **Momentum Gauges**: 1-month, 3-month, 6-month, and 12-month multi-timeframe price velocity.

### 3. Risk Analytics & Macroeconomic Stress Testing
- **Value at Risk (VaR 95%, 1-Day)**: Historical simulation quantile loss thresholds.
- **Conditional VaR (CVaR / Expected Shortfall)**: Average loss severity given that the 95% threshold is breached.
- **Risk-Adjusted Ratios**: Annualized Sharpe and Sortino ratios with explicit risk-free benchmark configuration.
- **Macroeconomic Stress Tests**: Hypothetical factor impacts during historical systemic shocks (2008 GFC, 2020 COVID crash, 2022 Fed Rate Hikes).

### 4. Historical Strategy Backtesting Lab
- **Strict Anti-Leakage Execution**: Trading signals generated on Close(t) execute strictly at Open(t+1) to prevent look-ahead bias.
- **Friction Modeling**: Explicit commission fees (default 0.10%) and market slippage (default 0.05%) deducted from every filled order.
- **Supported Strategies**:
  1. Moving Average Crossover (configurable fast/slow SMA)
  2. Relative Strength Index (RSI oversold buy / overbought exit)
  3. Momentum Rate-of-Change Breakout
  4. Mean Reversion (Bollinger Band lower-band reversals)
  5. Buy & Hold Benchmark comparison

### 5. Virtual Paper Trading & Portfolio Management
- **Zero Real-Money Risk**: Fully simulated practice accounts starting at ₹1,00,000 or $10,000.
- **Multi-Currency Auto-FX**: Trade international equities (NASDAQ, NYSE, NSE, BSE, LSE, TSE) with real-time conversion into your preferred account currency.
- **Portfolio Terminal & CSV Export**: Detailed transaction history, holdings breakdown, and one-click CSV export.

### 6. Explainable AI (XAI) & Sentiment Analysis
- **FinBERT Financial Sentiment**: Transformer-based tone analysis (Positive, Negative, Neutral) on live company earnings releases and headlines.
- **SHAP Game-Theoretic Attribution**: TreeExplainer and LinearExplainer attributing feature-level contributions to predictions.
- **Financial Document Intelligence (RAG)**: Semantic evidence retrieval across SEC 10-K and 10-Q disclosures powered by ChromaDB vector store.

### 7. Evaluator Demo Mode
- **Recruiter Fast-Track**: Pre-populated sample portfolio, pre-computed risk metrics, and strategy backtest results allowing project evaluation in under 3 minutes.

---

## 🛠 Technology Stack

| Layer | Technologies |
| :--- | :--- |
| **Frontend Frameworks** | Streamlit 1.37+ (Python), React 18 SPA (TypeScript / Tailwind CSS) |
| **Backend Services** | FastAPI 0.111, Uvicorn, Python 3.11 |
| **Database & ORM** | SQLite, SQLAlchemy 2.0 (11 relational schemas) |
| **Machine Learning** | Scikit-learn 1.4+, XGBoost 2.0+, Joblib |
| **Statistical Modeling** | SciPy (Student-t, linear regressions), NumPy, Pandas |
| **Explainable AI (XAI)** | SHAP 0.46+ (TreeExplainer, LinearExplainer) |
| **NLP & Sentiment** | HuggingFace Transformers, ProsusAI/finbert |
| **Document Retrieval (RAG)** | ChromaDB, Sentence-Transformers (`all-MiniLM-L6-v2`), PyPDF |
| **Generative Co-Pilot** | Google Gemini API (`gemini-3.8-flash`) |
| **Market Data Ingestion** | Yahoo Finance (yfinance), Finnhub API, SEC EDGAR |
| **Visualization** | Plotly Graph Objects, Plotly Express |

---

## 📐 Architecture Overview

```
                                ┌──────────────────────────────────────────────┐
                                │          FinPilot AI Client Terminals        │
                                ├───────────────────────┬──────────────────────┤
                                │  Streamlit Dashboard  │  React 18 SPA (FastAPI)│
                                │    (Port 8501 Cloud)  │       (Port 8000)    │
                                └───────────┬───────────┴──────────┬───────────┘
                                            │                      │
                                            ▼                      ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                           Orchestration & Analytics Layer                    │
├───────────────────────┬──────────────────────────────┬───────────────────────┤
│ Return Forecasting    │ Risk Analytics & VaR         │ Strategy Backtesting  │
│ (Walk-forward RF)     │ (Historical Simulation, CVaR)│ (Anti-leakage Open t+1│
├───────────────────────┼──────────────────────────────┼───────────────────────┤
│ FinBERT Sentiment     │ SHAP Explainability Engine   │ ChromaDB RAG Pipeline │
│ (ProsusAI Transformer)│ (Shapley Value Attributions) │ (SEC EDGAR Filings)   │
└───────────────────────┴──────────────┬───────────────┴───────────────────────┘
                                       │
                                       ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                             Data Ingestion & Storage                         │
├───────────────────────┬──────────────────────────────┬───────────────────────┤
│ Global Market Data    │ SQLite / PostgreSQL          │ Secure Secrets Bridge │
│ (22+ Exchanges via FX)│ (11 Relational Tables)       │ (st.secrets & .env)   │
└───────────────────────┴──────────────────────────────┴───────────────────────┘
```

---

## 🧠 Machine Learning & Forecasting Pipeline

FinPilot AI enforces strict time-series integrity:
1. **Chronological Splits**: Datasets are divided strictly chronologically: 65% Train, 15% Validation, 20% Test. Random shuffling is forbidden to prevent look-ahead bias.
2. **Model Selection**: The best classifier (Logistic Regression, Random Forest, or XGBoost) is chosen strictly based on validation ROC-AUC.
3. **Walk-Forward Magnitude Engine**: Rather than just predicting binary direction, the return forecasting engine fits walk-forward regression residuals to a calibrated Student-t distribution, generating empirical Bearish (5th percentile), Base (median), and Bullish (95th percentile) targets.

---

## ☁️ Streamlit Community Cloud Deployment

### 1-Minute Deployment Instructions:
1. Fork or push this repository to your GitHub account.
2. Navigate to [share.streamlit.io](https://share.streamlit.io/) and click **New app**.
3. Select your repository:
   - **Main file path**: `app.py` (or `streamlit_app.py`)
   - **Python version**: `3.11`
4. In **App Settings** → **Secrets**, configure your API keys:
   ```toml
   GEMINI_API_KEY = "your-gemini-key"
   GEMINI_MODEL = "gemini-3.8-flash"
   FINNHUB_API_KEY = "your-finnhub-key"
   SEC_USER_AGENT = "FinPilotAI research@university.edu"
   DATABASE_URL = "sqlite:///finpilot.db"
   MARKET_DATA_PROVIDER = "auto"
   NEWS_PROVIDER = "finnhub"
   ```
5. Click **Deploy!**

---

## 💻 Local Installation & Setup

```bash
# 1. Clone repository
git clone https://github.com/your-username/FinPilot-AI.git
cd FinPilot-AI

# 2. Create virtual environment
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# 3. Install pinned dependencies
pip install -r requirements.txt

# 4. Configure local environment variables
cp .env.example .env

# 5. Launch Streamlit terminal
streamlit run app.py
```

---

## 📚 Complete Technical Documentation

- 📘 [DEPLOYMENT.md](file:///c:/Users/Pranav/Downloads/FinPilot-AI/FinPilot-AI/DEPLOYMENT.md) — Step-by-step Streamlit Community Cloud deployment & secrets setup.
- 📐 [ARCHITECTURE.md](file:///c:/Users/Pranav/Downloads/FinPilot-AI/FinPilot-AI/ARCHITECTURE.md) — Complete multi-tier architecture & data flow diagrams.
- 🗂️ [MODEL_CARD.md](file:///c:/Users/Pranav/Downloads/FinPilot-AI/FinPilot-AI/MODEL_CARD.md) — Detailed governance cards for all predictive models.
- 🧪 [EXPERIMENTS.md](file:///c:/Users/Pranav/Downloads/FinPilot-AI/FinPilot-AI/EXPERIMENTS.md) — Walk-forward validation logs & empirical benchmarks.
- 🛡️ [SECURITY.md](file:///c:/Users/Pranav/Downloads/FinPilot-AI/FinPilot-AI/SECURITY.md) — Security controls, API privacy, and isolation guarantees.
- 🔬 [TESTING.md](file:///c:/Users/Pranav/Downloads/FinPilot-AI/FinPilot-AI/TESTING.md) — Automated test suite execution & verification records.

---

## ⚠️ Limitations & Financial Disclaimers

1. **Virtual Trading Only**: FinPilot AI has zero live broker connectivity. All account balances, transactions, and holdings are 100% simulated paper records.
2. **Not Financial Advice**: Predictions, model outputs, and risk analytics are strictly for quantitative research and educational demonstration.
3. **Historical Data Limitations**: Past volatility, correlations, and backtest results do not guarantee future market profitability.
