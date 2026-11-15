# FinPilot AI — System Architecture & Technical Specifications

This document outlines the architectural blueprints, data flow diagrams, and algorithmic methodologies of the **FinPilot AI** institutional platform.

---

## 🏛 1. Multi-Tier System Topology

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            PRESENTATION TIER                                │
├──────────────────────────────────────┬──────────────────────────────────────┤
│ Streamlit Institutional Terminal     │ React 18 SPA Financial Terminal     │
│ - 18 Specialized Fintech Modules     │ - Standalone Tailwind CSS Engine     │
│ - Plotly Interactive Visualizations  │ - Real-time WebSocket / REST Client │
│ - Web Audio API Synthesizer Tour     │ - Port 8000 Web Client              │
└──────────────────────────────────┬───┴──────────────────┬───────────────────┘
                                   │                      │
                                   ▼                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                       SERVICES & ORCHESTRATION TIER                         │
├─────────────────────────────────────────────────────────────────────────────┤
│ 1. ReturnForecastingEngine: Walk-Forward RF + Ridge + Student-t Calibration │
│ 2. InvestmentGoalSimulator: Non-Linear Daily & Weekly Compounding Hurdles   │
│ 3. MultiStockPortfolioSimulator: Markowitz Covariance & HHI Metrics         │
│ 4. PortfolioRiskAnalytics: 95% Historical VaR, CVaR, Sharpe & Stress Tests  │
│ 5. StrategyBacktester: Anti-Leakage Next-Bar Open Execution & Slippage       │
│ 6. PaperTradingEngine: Multi-Currency FX Engine & Virtual Cash Accounting   │
│ 7. FinBERTAnalyzer: HuggingFace ProsusAI Financial Sentiment Pipeline       │
│ 8. SHAPExplainer: TreeExplainer & LinearExplainer Feature Attributions       │
│ 9. FinancialRetriever: ChromaDB Vector Store & SEC EDGAR Semantic Ingestion │
│ 10. AIAssistant: Quantitative Co-Pilot & Natural Language Query Engine      │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           PERSISTENCE & DATA TIER                           │
├────────────────────────┬────────────────────────────┬───────────────────────┤
│ SQLAlchemy 2.0 ORM     │ Global Market Ingestion    │ Vector Database       │
│ - Users & Preferences  │ - Yahoo Finance (22+ Exch) │ - ChromaDB Embedded   │
│ - Virtual Accounts     │ - Finnhub Financial News   │ - Sentence-Transformer│
│ - Orders & Trades      │ - SEC EDGAR Filings (10-K) │ - Cosine Similarity   │
│ - Model Metrics & Logs │ - Deterministic Fallbacks  │ - 1000-char Chunks    │
└────────────────────────┴────────────────────────────┴───────────────────────┘
```

---

## 🔬 2. Machine Learning & Return Forecasting Methodology

### A. Chronological Splitting (Zero Look-Ahead Leakage)
Financial time series exhibit autocorrelation and non-stationarity. Traditional k-fold cross-validation or random shuffling leaks future information into past predictions. FinPilot AI strictly enforces chronological ordering:
$$\text{Train (65\%)} \longrightarrow \text{Validation (15\%)} \longrightarrow \text{Test (20\% Held-Out)}$$

### B. Walk-Forward Return Magnitude & Scenario Distribution
Rather than producing a naive point forecast, the `ReturnForecastingEngine`:
1. Fits an ensemble of **Random Forest Regressors** and **Ridge Regressors** over expanding rolling walk-forward windows.
2. Extracts out-of-sample forecast residuals: $e_t = R_t - \hat{R}_t$.
3. Fits the residuals to a **fat-tailed Student-t distribution** ($t(\nu, \mu, \sigma)$) to capture extreme market tail risks:
   $$\text{Bearish Scenario} = \hat{R}_{\text{base}} + t_{0.05}(\nu) \cdot \sigma_e$$
   $$\text{Base Scenario} = \text{Median}(\hat{R}_{\text{ensemble}})$$
   $$\text{Bullish Scenario} = \hat{R}_{\text{base}} + t_{0.95}(\nu) \cdot \sigma_e$$
4. Deducts round-trip simulated transaction friction and slippage from projected monetary values.

---

## ⚡ 3. Risk Analytics & Mathematical Foundations

### A. Historical Value at Risk (VaR 95%)
$$VaR_{\alpha} = -Q_{\alpha}(R_p) \times V_{\text{portfolio}}$$
where $Q_{0.05}(R_p)$ is the 5th percentile empirical daily return of the portfolio.

### B. Conditional Value at Risk (CVaR / Expected Shortfall)
$$CVaR_{\alpha} = -\mathbb{E}[R_p \mid R_p \le -VaR_{\alpha}] \times V_{\text{portfolio}}$$

### C. Markowitz Portfolio Variance
$$\sigma_p^2 = \mathbf{w}^T \mathbf{\Sigma} \mathbf{w}$$
where $\mathbf{w}$ is the normalized asset weight vector and $\mathbf{\Sigma}$ is the $N \times N$ annualized covariance matrix of historical returns.

### D. Herfindahl-Hirschman Concentration Index (HHI)
$$HHI = \sum_{i=1}^N w_i^2$$

---

## 📉 4. Backtesting Engine Anti-Leakage Architecture

Standard backtesters commit look-ahead bias by calculating a signal on the Close of day $t$ and immediately executing at that same Close price. In live financial markets, a signal generated at 16:00 EST cannot be executed at the 16:00 price.

FinPilot AI eliminates this bias:
1. Indicators (Moving Averages, RSI, Bollinger Bands) are calculated using strictly completed bar closes up to day $t$.
2. Signals $\text{Signal}_t \in \{0, 1\}$ are generated at $\text{Close}_t$.
3. Orders are queued and filled at $\text{Open}_{t+1}$.
4. A commission fee of $0.10\%$ and slippage penalty of $0.05\%$ are deducted from the execution price:
   $$P_{\text{buy}} = \text{Open}_{t+1} \times (1 + \text{Slippage})$$
   $$P_{\text{sell}} = \text{Open}_{t+1} \times (1 - \text{Slippage})$$

---

## 🛡️ 5. Paper Trading & Currency Normalization

To allow realistic trading across US (`AAPL`), Indian (`RELIANCE.NS`), German (`SIE.DE`), and Japanese (`7203.T`) equities, the `PaperTradingEngine` maintains multi-currency FX rates.

All virtual portfolio valuations, cash balances, and P&L statements are automatically normalized into the user's chosen account currency (e.g. `INR` or `USD`) without mixing currencies or exposing the user to currency distortion.
