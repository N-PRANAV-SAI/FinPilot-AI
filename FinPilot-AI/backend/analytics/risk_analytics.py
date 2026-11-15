"""FinPilot AI — Portfolio Risk Analytics Engine.

Implements institutional risk metrics: Value at Risk (VaR), Conditional VaR (Expected Shortfall),
Sharpe ratio, Sortino ratio, max drawdown, asset covariance, and historical stress scenarios.
Provides detailed methodology explanations and assumption disclosures for every metric.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd
from scipy import stats

from backend.data.market_data import fetch_market_data, get_latest_price, validate_ticker
from backend.preprocessing.clean_data import clean_market_data

log = logging.getLogger(__name__)

# Standard historical macroeconomic stress scenarios
STRESS_SCENARIOS = [
    {
        "id": "covid_2020",
        "name": "2020 COVID-19 Liquidity Shock",
        "period": "Feb 2020 – Mar 2020",
        "market_shock_pct": -33.9,
        "volatility_surge_mult": 2.8,
        "description": "Rapid systemic market drawdown triggered by pandemic lockdowns, accompanied by VIX spiking above 80.",
    },
    {
        "id": "rate_hikes_2022",
        "name": "2022 Global Inflation & Rate Hike Cycle",
        "period": "Jan 2022 – Oct 2022",
        "market_shock_pct": -25.4,
        "volatility_surge_mult": 1.7,
        "description": "Prolonged valuation contraction across duration assets driven by 500bps of Fed tightening and supply shocks.",
    },
    {
        "id": "gfc_2008",
        "name": "2008 Great Financial Crisis",
        "period": "Oct 2007 – Mar 2009",
        "market_shock_pct": -56.8,
        "volatility_surge_mult": 3.4,
        "description": "Severe systemic banking solvency crisis and credit contraction with prolonged multi-year recovery hurdle.",
    },
    {
        "id": "tech_selloff_2018",
        "name": "Q4 2018 Trade Tension & Fed Taper Tantrum",
        "period": "Oct 2018 – Dec 2018",
        "market_shock_pct": -19.8,
        "volatility_surge_mult": 1.9,
        "description": "Sharp quarter-end selloff driven by US-China trade friction and quantitative tightening fears.",
    },
]

# Metric educational descriptions for financial transparency
METRIC_EXPLANATIONS = {
    "var_95": {
        "title": "Value at Risk (VaR 95%, 1-Day)",
        "definition": "The threshold loss over a 1-day horizon that will not be exceeded with 95% confidence.",
        "why_it_matters": "Mandated by Basel accords for capital adequacy; shows standard worst-case daily loss under normal market regimes.",
        "formula": "VaR_95 = -Percentile_{5%}(R_portfolio) * Portfolio_Value",
        "limitations": "Does NOT tell you what happens beyond the 95th percentile (the 'tail risk'). Assumes distribution stationarity.",
    },
    "cvar_95": {
        "title": "Conditional Value at Risk (CVaR / Expected Shortfall)",
        "definition": "The expected monetary loss given that the portfolio loss has breached the 95% VaR threshold.",
        "why_it_matters": "A coherent risk measure that addresses VaR's blind spot by quantifying the severity of extreme tail crashes.",
        "formula": "CVaR_95 = -E[R | R <= -VaR_95] * Portfolio_Value",
        "limitations": "Sample estimates are volatile if the historical observation window contains few extreme tail observations.",
    },
    "sharpe_ratio": {
        "title": "Sharpe Ratio (Annualized)",
        "definition": "Excess return generated per unit of total portfolio volatility.",
        "why_it_matters": "Determines whether portfolio gains are compensation for smart asset selection or simply taking excess volatility.",
        "formula": "Sharpe = (E[R_p] - R_f) / sigma_p * sqrt(252)",
        "limitations": "Penalizes upside volatility equally with downside volatility. Assumes normally distributed returns.",
    },
    "sortino_ratio": {
        "title": "Sortino Ratio (Annualized)",
        "definition": "Excess return generated per unit of downside semi-deviation.",
        "why_it_matters": "Improvement over Sharpe because investors generally welcome upside variance and only fear downside losses.",
        "formula": "Sortino = (E[R_p] - R_f) / Downside_Deviation * sqrt(252)",
        "limitations": "Requires sufficient negative return observations for statistical stability.",
    },
    "max_drawdown": {
        "title": "Maximum Drawdown (MDD)",
        "definition": "The largest peak-to-trough drop in total portfolio value before a new peak is reached.",
        "why_it_matters": "Crucial psychological metric; large drawdowns trigger forced investor liquidation or margin distress.",
        "formula": "MDD = min_{t} (V_t - max_{s <= t} V_s) / max_{s <= t} V_s",
        "limitations": "Path-dependent metric based on historical path; does not guarantee future drawdown will not be deeper.",
    },
    "hhi_concentration": {
        "title": "Herfindahl-Hirschman Concentration Index (HHI)",
        "definition": "Sum of squared asset portfolio weights, measuring asset concentration risk on a scale from 0 to 1.",
        "why_it_matters": "Identifies idiosyncratic single-stock vulnerability. HHI < 0.15 is highly diversified; > 0.25 is concentrated.",
        "formula": "HHI = sum_{i=1}^N (w_i)^2",
        "limitations": "Measures capital allocation concentration, not risk factor concentration (e.g. 5 tech stocks still share beta).",
    },
}


def compute_portfolio_risk_analytics(
    holdings: List[Dict[str, Any]],
    account_currency: str = "INR",
    total_portfolio_value: float = 100000.0,
    available_cash: float = 100000.0,
    risk_free_rate_ann: float = 0.045,
    benchmark_ticker: str = "^GSPC",
) -> Dict[str, Any]:
    """Compute comprehensive institutional risk metrics for any portfolio of holdings."""
    # Handle empty portfolio case cleanly
    if not holdings:
        return {
            "portfolio_value": total_portfolio_value,
            "available_cash": available_cash,
            "currency": account_currency,
            "is_empty": True,
            "message": "Portfolio currently holds 100% cash. No equity market risk.",
            "metrics": {
                "portfolio_volatility_ann_pct": 0.0,
                "sharpe_ratio": 0.0,
                "sortino_ratio": 0.0,
                "var_95_daily_pct": 0.0,
                "var_95_daily_amt": 0.0,
                "cvar_95_daily_pct": 0.0,
                "cvar_95_daily_amt": 0.0,
                "max_drawdown_pct": 0.0,
                "beta_vs_benchmark": 0.0,
                "hhi_concentration": 0.0,
                "diversification_ratio": 1.0,
            },
            "explanations": METRIC_EXPLANATIONS,
            "stress_tests": [],
            "correlation_matrix": {},
        }

    # Extract tickers and allocation values
    tickers = [h.get("ticker", "").upper().strip() for h in holdings if h.get("ticker")]
    invested_total = sum(float(h.get("current_value", 0.0) or 0.0) for h in holdings)
    total_val = max(total_portfolio_value, invested_total + available_cash)

    weights = {}
    for h in holdings:
        t = h.get("ticker", "").upper().strip()
        val = float(h.get("current_value", 0.0) or 0.0)
        weights[t] = (val / total_val) if total_val > 0 else 0.0

    # Herfindahl-Hirschman Index (HHI)
    cash_weight = (available_cash / total_val) if total_val > 0 else 0.0
    all_weights = list(weights.values()) + ([cash_weight] if cash_weight > 0 else [])
    hhi = sum(w ** 2 for w in all_weights)

    # Fetch 1-year returns for each asset
    asset_returns = {}
    asset_vols = {}

    for t in tickers:
        try:
            df = fetch_market_data(t, period="1y")
            df_c = clean_market_data(df)
            if not df_c.empty and len(df_c) >= 20:
                ret = df_c["Close"].pct_change().dropna()
                asset_returns[t] = ret
                asset_vols[t] = float(ret.std() * np.sqrt(252))
            else:
                asset_vols[t] = 0.25
        except Exception:
            asset_vols[t] = 0.25

    # Align daily return series
    corr_matrix = {}
    portfolio_daily_returns = pd.Series(dtype=float)
    port_vol_ann = 0.0
    diversification_ratio = 1.0

    if asset_returns:
        df_ret = pd.DataFrame(asset_returns).dropna()
        if len(df_ret) >= 20:
            # Correlation matrix
            corr_df = df_ret.corr()
            corr_matrix = {col: corr_df[col].to_dict() for col in corr_df.columns}

            # Portfolio daily return series
            port_weights_series = pd.Series({t: weights.get(t, 0.0) for t in df_ret.columns})
            portfolio_daily_returns = df_ret.dot(port_weights_series)
            port_vol_ann = float(portfolio_daily_returns.std() * np.sqrt(252))

            # Diversification Ratio: weighted avg asset vol / actual portfolio vol
            weighted_vol = sum(weights.get(t, 0.0) * asset_vols.get(t, 0.20) for t in df_ret.columns)
            if port_vol_ann > 0:
                diversification_ratio = round(weighted_vol / port_vol_ann, 2)
        else:
            port_vol_ann = sum(weights.get(t, 0.0) * asset_vols.get(t, 0.20) for t in tickers)
    else:
        port_vol_ann = 0.20 * (1.0 - cash_weight)

    # Value at Risk (Historical Simulation 95% 1-day)
    var_95_pct = 0.0
    cvar_95_pct = 0.0
    if not portfolio_daily_returns.empty and len(portfolio_daily_returns) >= 20:
        var_threshold = float(np.percentile(portfolio_daily_returns, 5))
        var_95_pct = abs(var_threshold) * 100
        tail_losses = portfolio_daily_returns[portfolio_daily_returns <= var_threshold]
        cvar_95_pct = abs(float(tail_losses.mean())) * 100 if not tail_losses.empty else var_95_pct * 1.3
    else:
        # Parametric Gaussian fallback: 1.645 * daily vol
        daily_sigma = port_vol_ann / np.sqrt(252)
        var_95_pct = 1.645 * daily_sigma * 100
        cvar_95_pct = 2.063 * daily_sigma * 100

    var_95_amt = (var_95_pct / 100.0) * total_val
    cvar_95_amt = (cvar_95_pct / 100.0) * total_val

    # Sharpe and Sortino Ratios
    sharpe_ratio = 0.0
    sortino_ratio = 0.0
    max_dd_pct = 0.0

    if not portfolio_daily_returns.empty and len(portfolio_daily_returns) >= 20:
        mean_excess = portfolio_daily_returns.mean() - (risk_free_rate_ann / 252)
        if portfolio_daily_returns.std() > 0:
            sharpe_ratio = float(mean_excess / portfolio_daily_returns.std() * np.sqrt(252))

        downside = portfolio_daily_returns[portfolio_daily_returns < 0]
        if not downside.empty and downside.std() > 0:
            sortino_ratio = float(mean_excess / downside.std() * np.sqrt(252))

        cum_port = (1.0 + portfolio_daily_returns).cumprod()
        running_peak = cum_port.cummax()
        dd_series = (cum_port - running_peak) / running_peak
        max_dd_pct = abs(float(dd_series.min())) * 100

    # Beta vs Benchmark
    beta = 1.0 * (1.0 - cash_weight)
    try:
        df_bm = clean_market_data(fetch_market_data(benchmark_ticker, period="1y"))
        if not df_bm.empty and not portfolio_daily_returns.empty:
            bm_ret = df_bm["Close"].pct_change().dropna()
            aligned = pd.concat([portfolio_daily_returns, bm_ret], axis=1).dropna()
            if len(aligned) >= 20:
                cov = np.cov(aligned.iloc[:, 0], aligned.iloc[:, 1])[0, 1]
                var_b = np.var(aligned.iloc[:, 1])
                if var_b > 0:
                    beta = float(cov / var_b)
    except Exception:
        pass

    # Historical Macroeconomic Stress Scenario Projections
    stress_results = []
    equity_exposure = 1.0 - cash_weight
    for sc in STRESS_SCENARIOS:
        # Estimated impact based on portfolio beta and equity exposure
        est_shock = sc["market_shock_pct"] * beta * equity_exposure
        est_loss_amt = abs(est_shock / 100.0) * total_val
        stress_results.append({
            "id": sc["id"],
            "name": sc["name"],
            "period": sc["period"],
            "market_shock_pct": sc["market_shock_pct"],
            "portfolio_impact_pct": round(est_shock, 2),
            "portfolio_loss_amt": round(est_loss_amt, 2),
            "description": sc["description"],
        })

    return {
        "portfolio_value": round(total_val, 2),
        "available_cash": round(available_cash, 2),
        "cash_allocation_pct": round(cash_weight * 100, 1),
        "equity_allocation_pct": round(equity_exposure * 100, 1),
        "currency": account_currency,
        "is_empty": False,
        "holdings_count": len(holdings),
        "metrics": {
            "portfolio_volatility_ann_pct": round(port_vol_ann * 100, 2),
            "sharpe_ratio": round(sharpe_ratio, 2),
            "sortino_ratio": round(sortino_ratio, 2),
            "var_95_daily_pct": round(var_95_pct, 2),
            "var_95_daily_amt": round(var_95_amt, 2),
            "cvar_95_daily_pct": round(cvar_95_pct, 2),
            "cvar_95_daily_amt": round(cvar_95_amt, 2),
            "max_drawdown_pct": round(max_dd_pct, 2),
            "beta_vs_benchmark": round(beta, 2),
            "hhi_concentration": round(hhi, 3),
            "concentration_tier": "Highly Diversified" if hhi < 0.15 else ("Moderate" if hhi < 0.25 else "Concentrated"),
            "diversification_ratio": diversification_ratio,
        },
        "explanations": METRIC_EXPLANATIONS,
        "stress_tests": stress_results,
        "correlation_matrix": corr_matrix,
        "assumptions": {
            "risk_free_rate_ann_pct": risk_free_rate_ann * 100,
            "var_horizon": "1 Trading Day",
            "confidence_level": "95%",
            "annualization_factor": "252 Trading Days",
            "benchmark": benchmark_ticker,
        },
    }
