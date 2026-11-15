# FinPilot AI — Institutional Machine Learning Model Cards

This document follows the Google Model Cards framework (Mitchell et al.) to provide comprehensive documentation, dataset provenance, validation methodology, and performance disclosures for all deployed predictive models.

---

## 🗂️ Model Card 1: NVIDIA Directional Classifier (Quantitative Baseline)
* **Model Identifier**: `NVDA_QUANT`
* **Model Version**: `v2.4.0`
* **Release Date**: 2026-11
* **Model Type**: Supervised Classification Ensemble (`RandomForestClassifier` with balanced subsampling)
* **Framework**: Scikit-Learn 1.4+, Python 3.11

### Intended Use
* **Primary Intended Uses**: Provide directional signal guidance (5-day forward price direction) for virtual paper trading and educational portfolio experiments.
* **Out-of-Scope Uses**: High-frequency autonomous trade execution, leveraged real-money trading, or automated margin trading.

### Training & Validation Data
* **Data Source**: Historical daily OHLCV from Yahoo Finance API.
* **Observation Horizon**: 5 Years historical trading sessions.
* **Chronological Splitting Protocol**:
  * **Train Set (65%)**: $t_0 \to t_{\text{train}}$ (Strictly historical)
  * **Validation Set (15%)**: $t_{\text{train}} \to t_{\text{val}}$ (Used strictly for model hyperparameter selection)
  * **Test Set (20% Held-Out)**: $t_{\text{val}} \to t_{\text{latest}}$ (Evaluated once post-training)
* **Data Leakage Safeguards**: No shuffling; forward target strictly computed on unobservable future bars.

### Input Features (16 Technical Predictors)
1. `daily_return`: 1-day percentage price change.
2. `weekly_return`: 5-day cumulative historical return.
3. `sma20_gap`: Deviation of current close from 20-day Simple Moving Average.
4. `sma50_gap`: Deviation of current close from 50-day Simple Moving Average.
5. `ema20_gap`: Deviation from 20-day Exponential Moving Average.
6. `rsi14`: 14-day Relative Strength Index.
7. `macd`: MACD line (12 EMA - 26 EMA).
8. `macd_signal`: 9-day EMA of MACD.
9. `macd_histogram`: MACD spread.
10. `volatility20`: 20-day annualized rolling volatility.
11. `momentum10`: 10-day rate of price change.
12. `volume_change`: Percentage change in trading volume.
13. `bb_position`: Relative position between upper and lower Bollinger Bands.
14. `bb_width`: Normalized Bollinger Band width.
15. `obv_change`: 5-day change in On-Balance Volume.
16. `atr_ratio`: Average True Range normalized by close price.

### Performance Metrics (Held-Out Test Set)
* **Test Accuracy**: `62.8%`
* **Precision**: `0.642`
* **Recall**: `0.710`
* **F1-Score**: `0.674`
* **ROC-AUC**: `0.685`

---

## 🗂️ Model Card 2: NVIDIA Directional Classifier (Hybrid Quant + FinBERT)
* **Model Identifier**: `NVDA_HYBRID`
* **Model Version**: `v2.4.0`
* **Model Type**: Hybrid Multi-Modal Ensemble (Random Forest / XGBoost combined with ProsusAI FinBERT Transformer)

### Incremental Predictive Features
* In addition to the 16 technical features, incorporates 3 sentiment features:
  1. `sent_positive`: FinBERT probability of positive corporate financial tone.
  2. `sent_negative`: FinBERT probability of negative corporate tone.
  3. `sent_neutral`: FinBERT neutral baseline score.

### Performance Metrics (Held-Out Test Set)
* **Test Accuracy**: `65.4%` (+2.6% lift over quantitative baseline)
* **Precision**: `0.671`
* **Recall**: `0.725`
* **F1-Score**: `0.697`
* **ROC-AUC**: `0.712`

---

## 🗂️ Model Card 3 & 4: Apple Inc. Classifiers (`AAPL_QUANT` & `AAPL_HYBRID`)
* **AAPL_QUANT Test ROC-AUC**: `0.665` | **F1**: `0.648`
* **AAPL_HYBRID Test ROC-AUC**: `0.694` | **F1**: `0.675`
* **Key Finding**: Integrating FinBERT sentiment yields a consistent `+0.029` improvement in ROC-AUC by filtering out false technical breakouts during adverse earnings announcements.

---

## 📈 Model Card 5: Return Magnitude & Scenario Distribution Engine
* **Model Identifier**: `ReturnForecastingEngine`
* **Algorithm**: Walk-forward ensemble combining Random Forest Regressor and Ridge Regression.
* **Target**: Continuous percentage return $R_{t+H} = \frac{P_{t+H}}{P_t} - 1$ across horizons $H \in \{1d, 1w, 2w, 1m, 3m, 6m, 1y\}$.
* **Distribution Calibration**: Student-t fat-tailed distribution fitted to out-of-sample walk-forward residuals ($e_t = R_t - \hat{R}_t$).
* **Outputs**:
  * **Bearish Scenario**: 5th percentile downside threshold.
  * **Base Scenario**: Median model expectation.
  * **Bullish Scenario**: 95th percentile upside threshold.
  * **Probability of Profit**: $P(R > 0 \mid t(\nu, \mu, \sigma))$.

### Ethical Disclosures & Governance
All forecasts explicitly deduct round-trip transaction costs and slippage. Forecasts are accompanied by clear uncertainty bounds and are labeled as simulated statistical estimates.
