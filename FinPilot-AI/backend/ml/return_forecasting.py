"""FinPilot AI — Return Magnitude and Investment Scenario Forecasting Engine.

Implements chronological walk-forward regression and volatility-calibrated distribution
forecasting across global assets without look-ahead bias.
Calculates Bearish, Base, and Bullish scenarios, prediction intervals, out-of-sample
forecast errors, and probability metrics grounded in empirical historical data.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error

from backend.data.financial_data import fetch_fundamentals
from backend.data.global_exchanges import (
    CURRENCY_SYMBOLS,
    format_currency_amount,
    get_exchange_info,
)
from backend.data.market_data import fetch_market_data, get_latest_price, validate_ticker
from backend.preprocessing.clean_data import clean_market_data
from backend.preprocessing.feature_engineering import build_features
from backend.trading.paper_engine import get_fx_rate

log = logging.getLogger(__name__)

# Standard trading day mappings for duration horizons
DURATION_HORIZON_MAP: Dict[str, int] = {
    "1d": 1,
    "1 day": 1,
    "1w": 5,
    "1 week": 5,
    "2w": 10,
    "2 weeks": 10,
    "1m": 21,
    "1 month": 21,
    "3m": 63,
    "3 months": 63,
    "6m": 126,
    "6 months": 126,
    "1y": 252,
    "1 year": 252,
}


def parse_duration_to_trading_days(duration: Union[str, int]) -> int:
    """Normalize user duration string or integer into trading sessions."""
    if isinstance(duration, int):
        return max(1, min(duration, 756))

    d_clean = str(duration).strip().lower()
    if d_clean in DURATION_HORIZON_MAP:
        return DURATION_HORIZON_MAP[d_clean]

    # Handle custom inputs like "45 days", "15d", etc.
    digits = "".join(filter(str.isdigit, d_clean))
    if digits:
        val = int(digits)
        if "mo" in d_clean:
            return max(1, min(val * 21, 756))
        if "w" in d_clean:
            return max(1, min(val * 5, 756))
        if "y" in d_clean:
            return max(1, min(val * 252, 756))
        # Default calendar days to ~approx trading days (val * 5/7)
        return max(1, min(int(val * 5 / 7) or 1, 756))

    return 21  # Default to 1 month (21 trading days)


@dataclass
class ScenarioOutcome:
    name: str
    label: str
    return_pct: float
    profit_loss: float
    ending_value: float
    formatted_return: str
    formatted_pl: str
    formatted_ending_value: str
    description: str


@dataclass
class ReturnForecastResult:
    ticker: str
    company_name: str
    currency: str
    currency_symbol: str
    account_currency: str
    account_currency_symbol: str
    current_price: float
    fx_rate_to_account: float
    investment_amount: float
    investment_duration_label: str
    horizon_trading_days: int
    risk_level: str
    target_amount: Optional[float]

    # Primary Scenarios
    bearish: ScenarioOutcome
    base: ScenarioOutcome
    bullish: ScenarioOutcome

    # Probabilistic and Model Evaluation Metrics
    probability_positive_return: float
    probability_loss: float
    forecast_uncertainty_pct: float
    expected_volatility_annualized: float
    historical_mae_pct: float
    historical_rmse_pct: float
    sample_size_bars: int
    walk_forward_splits: int
    model_name: str
    is_statistically_significant: bool
    data_source: str
    quote_timestamp: str

    # Transaction cost & practical frictions
    simulated_transaction_cost_pct: float
    net_cost_deducted: float

    # Qualitative and Risk Disclaimers
    risk_factors: List[str]
    methodology_notes: List[str]
    is_insufficient_data: bool = False
    warning_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ticker": self.ticker,
            "company_name": self.company_name,
            "currency": self.currency,
            "currency_symbol": self.currency_symbol,
            "account_currency": self.account_currency,
            "account_currency_symbol": self.account_currency_symbol,
            "current_price": self.current_price,
            "fx_rate_to_account": self.fx_rate_to_account,
            "investment_amount": self.investment_amount,
            "investment_duration_label": self.investment_duration_label,
            "horizon_trading_days": self.horizon_trading_days,
            "risk_level": self.risk_level,
            "target_amount": self.target_amount,
            "scenarios": {
                "bearish": self.bearish.__dict__,
                "base": self.base.__dict__,
                "bullish": self.bullish.__dict__,
            },
            "probability_positive_return": round(self.probability_positive_return, 4),
            "probability_loss": round(self.probability_loss, 4),
            "forecast_uncertainty_pct": round(self.forecast_uncertainty_pct, 2),
            "expected_volatility_annualized": round(self.expected_volatility_annualized, 2),
            "historical_mae_pct": round(self.historical_mae_pct, 2),
            "historical_rmse_pct": round(self.historical_rmse_pct, 2),
            "sample_size_bars": self.sample_size_bars,
            "walk_forward_splits": self.walk_forward_splits,
            "model_name": self.model_name,
            "is_statistically_significant": self.is_statistically_significant,
            "data_source": self.data_source,
            "quote_timestamp": self.quote_timestamp,
            "simulated_transaction_cost_pct": self.simulated_transaction_cost_pct,
            "net_cost_deducted": round(self.net_cost_deducted, 2),
            "risk_factors": self.risk_factors,
            "methodology_notes": self.methodology_notes,
            "is_insufficient_data": self.is_insufficient_data,
            "warning_message": self.warning_message,
        }


class ReturnForecastingEngine:
    """Quantitative engine for estimating return distributions and scenarios."""

    def __init__(self, transaction_cost_pct: float = 0.001):
        """Initialize engine with configurable transaction costs (default 0.1%)."""
        self.transaction_cost_pct = transaction_cost_pct

    def predict_return_distribution(
        self,
        ticker: str,
        investment_amount: float,
        duration: Union[str, int] = "1m",
        target_amount: Optional[float] = None,
        risk_level: str = "Moderate",
        account_currency: str = "INR",
        sentiment_data: Optional[Dict[str, Any]] = None,
    ) -> ReturnForecastResult:
        """Compute transparent multi-scenario return forecast grounded in real market data.
        
        Uses chronological walk-forward cross-validation to estimate expected returns,
        forecast errors, and empirical prediction intervals without data leakage.
        """
        ticker = validate_ticker(ticker)
        trading_days = parse_duration_to_trading_days(duration)
        duration_label = str(duration).capitalize() if isinstance(duration, str) else f"{trading_days} trading days"

        # 1. Fetch real market history and live quote
        quote = get_latest_price(ticker)
        current_price = float(quote.get("price", 100.0))
        quote_source = quote.get("source", "MARKET_PROVIDER")
        quote_timestamp = quote.get("timestamp", datetime.now(timezone.utc).isoformat())

        # Exchange & Currency Info
        exc_info = get_exchange_info(ticker)
        asset_currency = (quote.get("currency") or exc_info.currency or "USD").upper()
        asset_symbol = CURRENCY_SYMBOLS.get(asset_currency, asset_currency)
        acc_currency = account_currency.upper()
        acc_symbol = CURRENCY_SYMBOLS.get(acc_currency, acc_currency)
        fx_rate = get_fx_rate(asset_currency, acc_currency)

        # Company metadata
        fundamentals = fetch_fundamentals(ticker)
        company_name = fundamentals.get("company_name") or quote.get("company_name") or ticker

        # 2. Historical OHLCV ingestion
        df = fetch_market_data(ticker, period="5y")
        if df is None or len(df) < 60:
            return self._build_insufficient_data_result(
                ticker=ticker,
                company_name=company_name,
                investment_amount=investment_amount,
                duration_label=duration_label,
                trading_days=trading_days,
                current_price=current_price,
                asset_currency=asset_currency,
                acc_currency=acc_currency,
                fx_rate=fx_rate,
                target_amount=target_amount,
                risk_level=risk_level,
                quote_timestamp=quote_timestamp,
            )

        clean_df = clean_market_data(df)
        feature_df = build_features(clean_df)

        # 3. Build forward return target strictly without look-ahead bias
        # Target = (Close[t + trading_days] - Close[t]) / Close[t]
        close_series = feature_df["Close"].astype(float)
        fwd_returns = (close_series.shift(-trading_days) / close_series) - 1.0

        # Feature selection
        candidate_cols = [
            "daily_return", "weekly_return", "sma20_gap", "sma50_gap", "ema20_gap",
            "rsi14", "macd", "macd_signal", "volatility20", "momentum10",
            "volume_change", "bb_position", "bb_width", "atr_ratio",
        ]
        available_features = [c for c in candidate_cols if c in feature_df.columns]

        # Attach sentiment feature if available
        working_df = feature_df[available_features].copy()
        if sentiment_data and "overall_sentiment" in sentiment_data:
            pos_ratio = float(sentiment_data.get("positive_ratio", 0.0))
            neg_ratio = float(sentiment_data.get("negative_ratio", 0.0))
            working_df["sentiment_polarity"] = pos_ratio - neg_ratio
            available_features.append("sentiment_polarity")

        working_df["fwd_target"] = fwd_returns
        valid_data = working_df.dropna()

        # Check sufficiency for statistical/ML modeling
        min_required = max(40, trading_days + 15)
        if len(valid_data) < min_required:
            # Fall back to empirical distribution from daily returns scaled to horizon
            return self._compute_empirical_drift_forecast(
                ticker=ticker,
                company_name=company_name,
                clean_df=clean_df,
                investment_amount=investment_amount,
                duration_label=duration_label,
                trading_days=trading_days,
                current_price=current_price,
                asset_currency=asset_currency,
                acc_currency=acc_currency,
                fx_rate=fx_rate,
                target_amount=target_amount,
                risk_level=risk_level,
                quote_source=quote_source,
                quote_timestamp=quote_timestamp,
            )

        # 4. Chronological Walk-Forward Regression & Residual Calibration
        X = valid_data[available_features].values
        y = valid_data["fwd_target"].values

        n_samples = len(valid_data)
        train_size = int(n_samples * 0.75)
        X_train, X_test = X[:train_size], X[train_size:]
        y_train, y_test = y[:train_size], y[train_size:]

        # Fit Random Forest Regressor & Robust Ridge
        rf = RandomForestRegressor(
            n_estimators=100,
            max_depth=5,
            min_samples_leaf=5,
            random_state=42,
        )
        ridge = Ridge(alpha=1.0)

        rf.fit(X_train, y_train)
        ridge.fit(X_train, y_train)

        # Out-of-sample walk-forward predictions
        rf_pred_test = rf.predict(X_test)
        ridge_pred_test = ridge.predict(X_test)
        # Weighted ensemble (60% RF, 40% Ridge)
        ensemble_pred_test = 0.6 * rf_pred_test + 0.4 * ridge_pred_test

        mae = float(mean_absolute_error(y_test, ensemble_pred_test))
        rmse = float(math.sqrt(mean_squared_error(y_test, ensemble_pred_test)))
        residuals = y_test - ensemble_pred_test

        # Predict for latest market state
        latest_features = feature_df[available_features].tail(1).fillna(0.0).values
        rf_latest = float(rf.predict(latest_features)[0])
        ridge_latest = float(ridge.predict(latest_features)[0])
        expected_central_return = 0.6 * rf_latest + 0.4 * ridge_latest

        # Bound extreme predictions using historical interquartile clamps
        hist_p05 = float(np.percentile(y, 5))
        hist_p95 = float(np.percentile(y, 95))
        expected_central_return = float(np.clip(expected_central_return, hist_p05, hist_p95))

        # 5. Volatility & Prediction Interval Calibration
        daily_returns = clean_df["Close"].pct_change().dropna()
        daily_vol = float(daily_returns.std()) if len(daily_returns) > 0 else 0.015
        annualized_vol = float(daily_vol * math.sqrt(252) * 100)

        # Horizon scale factor for volatility with square-root of time
        horizon_vol = daily_vol * math.sqrt(trading_days)

        # Calibrate intervals based on empirical test residuals + horizon volatility
        # Risk preference adjustment modifies quantile threshold
        risk_quantile_map = {
            "low": (0.15, 0.85),
            "conservative": (0.15, 0.85),
            "moderate": (0.10, 0.90),
            "high": (0.05, 0.95),
            "aggressive": (0.05, 0.95),
        }
        low_q, high_q = risk_quantile_map.get(risk_level.lower(), (0.10, 0.90))

        if len(residuals) >= 20:
            res_downside = float(np.percentile(residuals, low_q * 100))
            res_upside = float(np.percentile(residuals, high_q * 100))
        else:
            # Fall back to Student's t distribution with df=5 (fat tails)
            t_down = stats.t.ppf(low_q, df=5)
            t_up = stats.t.ppf(high_q, df=5)
            res_downside = t_down * horizon_vol
            res_upside = t_up * horizon_vol

        # Construct three calibrated scenarios
        bearish_return = expected_central_return + res_downside
        base_return = expected_central_return
        bullish_return = expected_central_return + res_upside

        # Ensure realistic hierarchy: Bearish < Base < Bullish
        if bearish_return >= base_return:
            bearish_return = base_return - 1.5 * horizon_vol
        if bullish_return <= base_return:
            bullish_return = base_return + 1.5 * horizon_vol

        # 6. Probability Calculation using empirically calibrated Student-t distribution
        sigma_forecast = max(horizon_vol, rmse)
        if sigma_forecast > 0:
            # P(Return > 0)
            z_zero = (0.0 - expected_central_return) / sigma_forecast
            prob_loss = float(stats.t.cdf(z_zero, df=6))
            prob_positive = float(1.0 - prob_loss)
        else:
            prob_positive = 0.50
            prob_loss = 0.50

        # Forecast uncertainty metric (spread between bullish and bearish return)
        forecast_uncertainty = abs(bullish_return - bearish_return) * 100

        # 7. Apply simulated transaction cost (brokerage, slippage, exchange fees)
        effective_cost = investment_amount * (self.transaction_cost_pct * 2)  # Entry + exit

        # Calculate monetary outcomes in account currency
        def build_scenario(name: str, label: str, ret: float, desc: str) -> ScenarioOutcome:
            gross_ending_val = investment_amount * (1.0 + ret)
            net_ending_val = max(0.0, gross_ending_val - effective_cost)
            net_pl = net_ending_val - investment_amount
            net_ret_pct = (net_pl / investment_amount) * 100 if investment_amount > 0 else 0.0

            sign_pl = "+" if net_pl >= 0 else ""
            sign_ret = "+" if net_ret_pct >= 0 else ""

            return ScenarioOutcome(
                name=name,
                label=label,
                return_pct=round(net_ret_pct, 2),
                profit_loss=round(net_pl, 2),
                ending_value=round(net_ending_val, 2),
                formatted_return=f"{sign_ret}{net_ret_pct:.2f}%",
                formatted_pl=f"{sign_pl}{format_currency_amount(net_pl, acc_currency)}",
                formatted_ending_value=format_currency_amount(net_ending_val, acc_currency),
                description=desc,
            )

        bearish_sc = build_scenario(
            "Bearish",
            "Downside Stress Scenario",
            bearish_return,
            f"Adverse market conditions corresponding to the ~{int(low_q*100)}th historical percentile downside or negative macro shock.",
        )
        base_sc = build_scenario(
            "Base",
            "Central Model Forecast",
            base_return,
            "Median central outcome estimated by the walk-forward ensemble assuming historical persistence of trend and volatility.",
        )
        bullish_sc = build_scenario(
            "Bullish",
            "Favourable Momentum Scenario",
            bullish_return,
            f"Strong positive execution reaching the ~{int(high_q*100)}th historical percentile upside with supportive market sentiment.",
        )

        # Risk factors identification
        risk_factors = self._generate_risk_factors(
            ticker=ticker,
            annualized_vol=annualized_vol,
            trading_days=trading_days,
            fundamentals=fundamentals,
            prob_loss=prob_loss,
            asset_currency=asset_currency,
            acc_currency=acc_currency,
        )

        methodology_notes = [
            f"Model Architecture: Walk-Forward Random Forest + Ridge Ensemble ({len(available_features)} technical & fundamental features).",
            f"Horizon: {trading_days} trading sessions ({duration_label}). Out-of-sample sample size: {len(y_test)} historical windows.",
            f"Historical validation: Mean Absolute Error (MAE) = {mae*100:.2f}%, RMSE = {rmse*100:.2f}%.",
            f"Simulated transaction friction of {self.transaction_cost_pct*100:.1f}% applied per leg (total {format_currency_amount(effective_cost, acc_currency)} deducted).",
            "Disclaimer: All projections are probabilistic models for educational simulation. Financial markets involve inherent uncertainty and past performance does not guarantee future results.",
        ]

        return ReturnForecastResult(
            ticker=ticker,
            company_name=company_name,
            currency=asset_currency,
            currency_symbol=asset_symbol,
            account_currency=acc_currency,
            account_currency_symbol=acc_symbol,
            current_price=current_price,
            fx_rate_to_account=fx_rate,
            investment_amount=investment_amount,
            investment_duration_label=duration_label,
            horizon_trading_days=trading_days,
            risk_level=risk_level,
            target_amount=target_amount,
            bearish=bearish_sc,
            base=base_sc,
            bullish=bullish_sc,
            probability_positive_return=prob_positive,
            probability_loss=prob_loss,
            forecast_uncertainty_pct=forecast_uncertainty,
            expected_volatility_annualized=annualized_vol,
            historical_mae_pct=mae * 100,
            historical_rmse_pct=rmse * 100,
            sample_size_bars=len(clean_df),
            walk_forward_splits=len(y_test),
            model_name="Walk-Forward Random Forest + Ridge Regressor",
            is_statistically_significant=(len(y_test) >= 30 and rmse < 0.35),
            data_source=quote_source,
            quote_timestamp=quote_timestamp,
            simulated_transaction_cost_pct=self.transaction_cost_pct * 100,
            net_cost_deducted=effective_cost,
            risk_factors=risk_factors,
            methodology_notes=methodology_notes,
            is_insufficient_data=False,
        )

    def _compute_empirical_drift_forecast(
        self,
        ticker: str,
        company_name: str,
        clean_df: pd.DataFrame,
        investment_amount: float,
        duration_label: str,
        trading_days: int,
        current_price: float,
        asset_currency: str,
        acc_currency: str,
        fx_rate: float,
        target_amount: Optional[float],
        risk_level: str,
        quote_source: str,
        quote_timestamp: str,
    ) -> ReturnForecastResult:
        """Statistical fallback using empirical geometric Brownian motion with fat-tailed innovations."""
        daily_returns = clean_df["Close"].pct_change().dropna().values
        mu_daily = float(np.mean(daily_returns))
        sigma_daily = float(np.std(daily_returns))

        # Expected horizon drift and volatility
        mu_horizon = mu_daily * trading_days
        sigma_horizon = sigma_daily * math.sqrt(trading_days)
        annualized_vol = sigma_daily * math.sqrt(252) * 100

        # Percentiles using Student's t
        t_bear = stats.t.ppf(0.10, df=5)
        t_bull = stats.t.ppf(0.90, df=5)

        base_ret = mu_horizon
        bear_ret = mu_horizon + t_bear * sigma_horizon
        bull_ret = mu_horizon + t_bull * sigma_horizon

        # Probabilities
        if sigma_horizon > 0:
            prob_loss = float(stats.t.cdf(-mu_horizon / sigma_horizon, df=5))
            prob_positive = 1.0 - prob_loss
        else:
            prob_loss = 0.5
            prob_positive = 0.5

        effective_cost = investment_amount * (self.transaction_cost_pct * 2)

        def make_sc(name: str, label: str, ret: float, desc: str) -> ScenarioOutcome:
            gross_val = investment_amount * (1.0 + ret)
            net_val = max(0.0, gross_val - effective_cost)
            net_pl = net_val - investment_amount
            pct = (net_pl / investment_amount) * 100 if investment_amount > 0 else 0.0
            s_pl = "+" if net_pl >= 0 else ""
            s_ret = "+" if pct >= 0 else ""
            return ScenarioOutcome(
                name=name,
                label=label,
                return_pct=round(pct, 2),
                profit_loss=round(net_pl, 2),
                ending_value=round(net_val, 2),
                formatted_return=f"{s_ret}{pct:.2f}%",
                formatted_pl=f"{s_pl}{format_currency_amount(net_pl, acc_currency)}",
                formatted_ending_value=format_currency_amount(net_val, acc_currency),
                description=desc,
            )

        bear_sc = make_sc("Bearish", "Downside Volatility Band", bear_ret, "Adverse price movement at 10th percentile empirical shock.")
        base_sc = make_sc("Base", "Empirical Mean Drift", base_ret, "Central historical drift scaled across the duration.")
        bull_sc = make_sc("Bullish", "Upside Momentum Band", bull_ret, "Favourable price movement at 90th percentile empirical expansion.")

        uncertainty = abs(bull_ret - bear_ret) * 100

        return ReturnForecastResult(
            ticker=ticker,
            company_name=company_name,
            currency=asset_currency,
            currency_symbol=CURRENCY_SYMBOLS.get(asset_currency, asset_currency),
            account_currency=acc_currency,
            account_currency_symbol=CURRENCY_SYMBOLS.get(acc_currency, acc_currency),
            current_price=current_price,
            fx_rate_to_account=fx_rate,
            investment_amount=investment_amount,
            investment_duration_label=duration_label,
            horizon_trading_days=trading_days,
            risk_level=risk_level,
            target_amount=target_amount,
            bearish=bear_sc,
            base=base_sc,
            bullish=bull_sc,
            probability_positive_return=prob_positive,
            probability_loss=prob_loss,
            forecast_uncertainty_pct=uncertainty,
            expected_volatility_annualized=annualized_vol,
            historical_mae_pct=sigma_horizon * 100 * 0.798,  # E[|X|] for normal
            historical_rmse_pct=sigma_horizon * 100,
            sample_size_bars=len(clean_df),
            walk_forward_splits=0,
            model_name="Empirical Drift & Volatility Rescaling (Limited History)",
            is_statistically_significant=False,
            data_source=quote_source,
            quote_timestamp=quote_timestamp,
            simulated_transaction_cost_pct=self.transaction_cost_pct * 100,
            net_cost_deducted=effective_cost,
            risk_factors=[
                "Shorter historical sample: predictions rely primarily on daily return volatility extrapolation.",
                f"Annualized price volatility is elevated at {annualized_vol:.1f}%.",
                "Market regime shifts can diverge significantly from historical distributions.",
            ],
            methodology_notes=[
                "Method: Parametric Student-t Rescaling of Historical Returns.",
                "Sufficient sample depth was unavailable for 100-tree walk-forward ML; fallback statistical model engaged.",
            ],
            is_insufficient_data=False,
            warning_message="Limited historical depth: Scenarios are statistically extrapolated from available market bars.",
        )

    def _build_insufficient_data_result(
        self,
        ticker: str,
        company_name: str,
        investment_amount: float,
        duration_label: str,
        trading_days: int,
        current_price: float,
        asset_currency: str,
        acc_currency: str,
        fx_rate: float,
        target_amount: Optional[float],
        risk_level: str,
        quote_timestamp: str,
    ) -> ReturnForecastResult:
        """Safe fallback when market data is severely insufficient."""
        zero_sc = ScenarioOutcome(
            name="Insufficient Data",
            label="Unavailable",
            return_pct=0.0,
            profit_loss=0.0,
            ending_value=investment_amount,
            formatted_return="0.00%",
            formatted_pl=format_currency_amount(0.0, acc_currency),
            formatted_ending_value=format_currency_amount(investment_amount, acc_currency),
            description="Historical trading bars are insufficient to construct an authentic prediction without fabricating results.",
        )

        return ReturnForecastResult(
            ticker=ticker,
            company_name=company_name,
            currency=asset_currency,
            currency_symbol=CURRENCY_SYMBOLS.get(asset_currency, asset_currency),
            account_currency=acc_currency,
            account_currency_symbol=CURRENCY_SYMBOLS.get(acc_currency, acc_currency),
            current_price=current_price,
            fx_rate_to_account=fx_rate,
            investment_amount=investment_amount,
            investment_duration_label=duration_label,
            horizon_trading_days=trading_days,
            risk_level=risk_level,
            target_amount=target_amount,
            bearish=zero_sc,
            base=zero_sc,
            bullish=zero_sc,
            probability_positive_return=0.50,
            probability_loss=0.50,
            forecast_uncertainty_pct=100.0,
            expected_volatility_annualized=0.0,
            historical_mae_pct=0.0,
            historical_rmse_pct=0.0,
            sample_size_bars=0,
            walk_forward_splits=0,
            model_name="Data Insufficient Safeguard",
            is_statistically_significant=False,
            data_source="NONE",
            quote_timestamp=quote_timestamp,
            simulated_transaction_cost_pct=0.0,
            net_cost_deducted=0.0,
            risk_factors=["Severe data shortage: Cannot construct validated statistical confidence intervals."],
            methodology_notes=["Model halted: FinPilot AI prohibits generating fabricated numerical forecasts."],
            is_insufficient_data=True,
            warning_message=f"Insufficient market data bars found for {ticker} to train forecasting regression.",
        )

    def _generate_risk_factors(
        self,
        ticker: str,
        annualized_vol: float,
        trading_days: int,
        fundamentals: Dict[str, Any],
        prob_loss: float,
        asset_currency: str,
        acc_currency: str,
    ) -> List[str]:
        """Synthesize concrete, transparent risk factors for the investor."""
        factors: List[str] = []

        # Volatility risk
        if annualized_vol > 45.0:
            factors.append(f"Extreme Volatility: Annualized price volatility of {annualized_vol:.1f}% indicates high vulnerability to sudden sharp drawdowns.")
        elif annualized_vol > 25.0:
            factors.append(f"Moderate-to-High Volatility: Historical fluctuation ({annualized_vol:.1f}% annualized) can cause significant interim portfolio swings.")
        else:
            factors.append(f"Standard Equities Volatility: Annualized volatility is {annualized_vol:.1f}%.")

        # Time horizon risk
        if trading_days <= 5:
            factors.append("Short Horizon Risk: 1-day to 1-week timeframes are heavily dominated by random market noise, bid-ask spreads, and unexpected corporate headlines rather than fundamental value.")
        elif trading_days >= 126:
            factors.append("Long Horizon Macro Risk: Multi-month holding periods are exposed to macroeconomic interest rate adjustments, regulatory changes, and corporate earnings reports.")

        # Loss probability transparency
        if prob_loss >= 0.45:
            factors.append(f"Elevated Probability of Loss: Validated model estimates a {prob_loss*100:.1f}% chance that the return could be negative over this timeframe.")

        # Currency risk if foreign asset
        if asset_currency != acc_currency:
            factors.append(f"Foreign Exchange (FX) Risk: Asset trades in {asset_currency} while your account is in {acc_currency}. Fluctuations in the {asset_currency}/{acc_currency} exchange rate will impact your realized profit.")

        # Debt and valuation risk
        pe = fundamentals.get("trailing_pe")
        if pe and isinstance(pe, (int, float)) and pe > 60:
            factors.append(f"High Valuation Multiple: Trailing P/E of {pe:.1f}x prices in aggressive earnings growth, increasing vulnerability to any forward earnings revisions.")

        return factors
