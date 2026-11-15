# FinPilot AI — Streamlit Community Cloud Deployment Guide

This guide provides step-by-step instructions for deploying **FinPilot AI** to **Streamlit Community Cloud** from your GitHub repository.

---

## 📋 Prerequisites
1. A [GitHub](https://github.com/) account.
2. A [Streamlit Community Cloud](https://share.streamlit.io/) account (free).
3. Google Gemini API Key ([Google AI Studio](https://aistudio.google.com/)).
4. (Optional) Finnhub API Key ([Finnhub.io](https://finnhub.io/)).

---

## 🚀 Step 1: Prepare and Push to GitHub

### 1.1 Verify `.gitignore` Safety
Ensure that your `.env` file containing local API keys is **NOT** committed:
```bash
# Verify that .env and local databases are ignored:
git status --ignored
```
The repository includes `.gitignore` which automatically protects:
- `.env`
- `.streamlit/secrets.toml`
- `finpilot.db`
- `artifacts/logs/` & `artifacts/vector_db/`
- Virtual environment directories (`.venv/`)

### 1.2 Push to GitHub
```bash
git add .
git commit -m "feat: production readiness, fintech analytics suite & cloud deployment"
git push origin main
```

---

## ☁️ Step 2: Configure Streamlit Community Cloud

1. Log in to [share.streamlit.io](https://share.streamlit.io/).
2. Click **Create app** (or **New app**).
3. Select your repository: `your-username/FinPilot-AI`.
4. Set the configuration parameters:
   - **Branch**: `main`
   - **Main file path**: `app.py` (or `streamlit_app.py` if deploying from root repository)
   - **App URL**: Choose a custom subdomain (e.g., `finpilot-ai.streamlit.app`)

### 2.1 Advanced Settings — Python Version
Click **Advanced settings** (or the gear icon) and select:
- **Python version**: `3.11` (recommended for full scikit-learn, XGBoost, and PyTorch compatibility).

---

## 🔐 Step 3: Configure Streamlit Cloud Secrets

In your Streamlit Cloud app dashboard, go to:
**App Settings** → **Secrets**

Paste the following configuration (replace placeholders with your real API keys):

```toml
# ==============================================================================
# FinPilot AI — Cloud Production Secrets
# ==============================================================================

# 1. Generative AI (Google Gemini) - Free at https://aistudio.google.com/
GEMINI_API_KEY = "AIzaSyYourRealGeminiKeyHere"
GEMINI_MODEL = "gemini-3.8-flash"

# 2. Financial News API (Finnhub) - Free at https://finnhub.io/
FINNHUB_API_KEY = "your_real_finnhub_key_here"
NEWS_PROVIDER = "finnhub"

# 3. Market Data Provider Selection (yfinance works with zero configuration)
MARKET_DATA_PROVIDER = "auto"

# 4. Regulatory Filings (SEC EDGAR requirement: AppName contact@domain.com)
SEC_USER_AGENT = "FinPilotAI research@university.edu"

# 5. Database Connection (SQLite default for single-container cloud deployment)
DATABASE_URL = "sqlite:///finpilot.db"

# 6. Artifact Directories
MODEL_DIR = "artifacts/models"
CHROMA_DIR = "artifacts/vector_db"
LOG_DIR = "artifacts/logs"
```

Click **Save**. The app will automatically restart and inject these secrets into the runtime environment.

---

## 🔍 Step 4: Verify Deployment Acceptance Criteria

Once the build completes (typically 3–8 minutes on initial deploy), verify these steps:

| # | Acceptance Check | Expected Outcome |
| :---: | :--- | :--- |
| **1** | **Initial Page Load** | App loads with dark terminal theme and branding header (`🛫 FinPilot AI`). |
| **2** | **App Tour Walkthrough** | 10-scene interactive product walkthrough appears with **Skip Intro** button. |
| **3** | **Evaluator Demo Mode** | Clicking **🚀 Enter Guest Demo Mode** logs in immediately with sample portfolio. |
| **4** | **AI Profit Predictor** | Running a 1-month forecast on `NVDA` displays Bearish, Base, and Bullish scenarios. |
| **5** | **Goal Hurdle Simulator** | Setting ₹10,000 to ₹1,00,000 calculates required compounding rates across 6 horizons. |
| **6** | **Quant Research Lab** | Selecting `NVDA` renders rolling volatility bands, beta regression, and drawdowns. |
| **7** | **Risk Analytics** | Value at Risk (VaR 95%), CVaR, and stress scenarios calculate properly. |
| **8** | **Backtesting Lab** | Strategy backtest executes with zero look-ahead bias and renders equity curves. |
| **9** | **Data Quality Monitor** | Provider health badges display `ONLINE` / `CONNECTED`. |
| **10** | **Paper Trading Ticket** | Placing a simulated Buy order updates cash and holdings without real financial risk. |

---

## 🛠 Troubleshooting Common Cloud Issues

### 1. `ModuleNotFoundError: No module named 'scipy'` or `torch`
- **Cause**: Incomplete dependency cache.
- **Fix**: In your Streamlit Cloud app dashboard, click **Manage app** → **⋮** → **Reboot app** → **Clear cache and deploy**.

### 2. Missing Gemini / Finnhub API Key Warning
- **Cause**: Secrets not saved in Streamlit Cloud Secrets settings.
- **Fix**: Check **App Settings** → **Secrets** and ensure `GEMINI_API_KEY = "..."` is saved without extra quotes or spaces.

### 3. Database Persistence across Cold Starts
- **Note**: SQLite stored inside Streamlit Community Cloud ephemeral containers resets if the app undergoes an inactive cold restart (after 7 days of inactivity).
- **Production Solution**: For permanent multi-user persistence across restarts, supply a cloud PostgreSQL connection string (such as [Supabase](https://supabase.com/) or [Neon](https://neon.tech/)) in `DATABASE_URL`:
  ```toml
  DATABASE_URL = "postgresql://user:password@aws-0-region.pooler.supabase.com:6543/postgres"
  ```
