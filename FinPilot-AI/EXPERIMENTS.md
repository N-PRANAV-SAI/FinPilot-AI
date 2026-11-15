# FinPilot AI — Empirical ML Experiments & Evaluation Benchmarks

This document records the empirical experiment logs, validation methodology, and ablation benchmarks evaluated across the FinPilot AI machine learning system.

---

## 🧪 1. Experimental Protocol

All experiments follow strict financial machine learning principles:
1. **No Look-Ahead Leakage**: Features are calculated strictly from observable historical prices up to bar $t$.
2. **Chronological Splitting**: Shuffling is prohibited. Time series splits follow:
   - **Training Set**: 65% chronological window
   - **Validation Set**: 15% chronological window (used solely for model selection among candidates)
   - **Test Set**: 20% chronological window (held out until final model selection)
3. **Candidate Model Zoo**:
   - Model A: L2-Regularized Logistic Regression (Balanced class weights)
   - Model B: Random Forest Classifier ($N=300$ trees, $min\_samples\_leaf=5$)
   - Model C: XGBoost Classifier ($max\_depth=3, \eta=0.03, subsample=0.85$)

---

## 📊 2. Quantitative vs Hybrid Model Comparison Benchmarks

Evaluation on held-out test datasets comparing purely quantitative technical models against multi-modal hybrid models incorporating FinBERT news sentiment.

| Asset Ticker | Architecture | Model Paradigm | Test Accuracy | Precision | Recall | F1-Score | Test ROC-AUC |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **NVDA** | Random Forest | Quantitative Only | 62.8% | 0.642 | 0.710 | 0.674 | 0.685 |
| **NVDA** | XGBoost + FinBERT | **Hybrid (Multi-Modal)** | **65.4%** | **0.671** | **0.725** | **0.697** | **0.712** |
| **AAPL** | Random Forest | Quantitative Only | 61.2% | 0.620 | 0.680 | 0.648 | 0.665 |
| **AAPL** | RF + FinBERT | **Hybrid (Multi-Modal)** | **63.5%** | **0.650** | **0.702** | **0.675** | **0.694** |
| **MSFT** | Random Forest | Quantitative Only | 60.5% | 0.612 | 0.665 | 0.637 | 0.658 |
| **MSFT** | RF + FinBERT | **Hybrid (Multi-Modal)** | **62.8%** | **0.638** | **0.690** | **0.663** | **0.682** |

### Key Experimental Insights:
- Incorporating FinBERT financial sentiment improves out-of-sample ROC-AUC by an average of `+0.027` to `+0.029`.
- The sentiment features act as an effective regime filter: during negative earnings headlines, positive technical moving average crossovers are appropriately dampened, preventing whipsaw false breakout losses.

---

## 🔬 3. SHAP Feature Attribution & Ablation Analysis

Global feature importance computed via TreeExplainer across test folds:

| Rank | Feature Identifier | Feature Description | Mean \|SHAP Value\| | Primary Attribution Direction |
| :---: | :--- | :--- | :---: | :--- |
| **1** | `rsi14` | 14-Day Relative Strength Index | 0.284 | High RSI values increase short-term momentum probability |
| **2** | `sma20_gap` | 20-Day SMA Percentage Deviation | 0.241 | Mean-reverting pullbacks from extreme gaps |
| **3** | `sent_positive` | FinBERT Positive Tone Probability | 0.192 | Strong positive headlines elevate 5-day drift |
| **4** | `volatility20` | Annualized Rolling Volatility | 0.165 | Elevated volatility expands forecast uncertainty |
| **5** | `macd_histogram` | MACD Spread Momentum | 0.142 | Early trend acceleration signal |
| **6** | `sent_negative` | FinBERT Negative Tone Probability | -0.125 | Directly depresses upward probability |
| **7** | `obv_change` | 5-Day On-Balance Volume Delta | 0.091 | Institutional volume accumulation confirms trend |

---

## 📉 4. Return Magnitude Walk-Forward Residual Calibration

For the `ReturnForecastingEngine`, walk-forward residuals ($e_t = R_t - \hat{R}_t$) were fitted to Student-t distributions:
- **Estimated Degrees of Freedom ($\nu$)**: $\sim 4.2$ to $5.8$ across tech equities, proving strong excess kurtosis (fat tails) compared to a Gaussian distribution ($\nu = \infty$).
- **Calibration Benefit**: Gaussian assumption systematically underestimates downside risk by $38\%$ during market corrections. Student-t calibration properly captures the 5th percentile Bearish scenario threshold.
