"""FinPilot AI — Multi-Stock Investment and Correlated Portfolio Simulator.

Computes portfolio-level scenarios (Bearish, Base, Bullish) using historical variance-covariance
matrices, correlation coefficients, Herfindahl concentration, sector/country exposures,
and empirical maximum drawdown. Never simply sums independent un-correlated assets.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union

import numpy as np
import pandas as pd
from scipy import stats

from backend.data.financial_data import fetch_fundamentals
from backend.data.global_exchanges import (
    CURRENCY_SYMBOLS,
    format_currency_amount,
    get_exchange_info,
)
from backend.data.market_data import fetch_market_data, get_latest_price, validate_ticker
from backend.ml.return_forecasting import (
    ReturnForecastingEngine,
    ScenarioOutcome,
    parse_duration_to_trading_days,
)
from backend.preprocessing.clean_data import clean_market_data
from backend.trading.paper_engine import get_fx_rate

log = logging.getLogger(__name__)


@dataclass
class AssetAllocationInput:
    ticker: str
    allocation_amount: float


@dataclass
class AllocatedAssetDetail:
    ticker: str
    company_name: str
    exchange: str
    country: str
    sector: str
    currency: str
    latest_price: float
    fx_rate: float
    allocated_amount_account: float
    weight_pct: float
    expected_return_pct: float
    annualized_volatility_pct: float


@dataclass
class PortfolioSimulationResult:
    total_capital: float
    invested_capital: float
    cash_reserved: float
    cash_weight_pct: float
    account_currency: str
    duration_label: str
    horizon_trading_days: int

    # Assets breakdown
    assets: List[AllocatedAssetDetail]

    # Scenarios (Bearish, Base, Bullish)
    bearish: ScenarioOutcome
    base: ScenarioOutcome
    bullish: ScenarioOutcome

    # Risk & Analytical metrics
    portfolio_expected_return_pct: float
    portfolio_annualized_volatility_pct: float
    portfolio_horizon_volatility_pct: float
    estimated_max_drawdown_pct: float
    diversification_benefit_pct: float  # Weighted avg vol - portfolio vol
    hhi_concentration_index: float
    concentration_rating: str  # "Low", "Moderate", "High"
    top_holding_pct: float

    # Exposures
    country_exposure: Dict[str, float]
    sector_exposure: Dict[str, float]

    # Probabilities
    probability_positive_return: float
    probability_loss: float

    # Correlation Matrix
    correlation_matrix: Dict[str, Dict[str, float]]
    tickers_evaluated: List[str]

    # Risk & Transparency
    risk_factors: List[str]
    methodology_notes: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_capital": self.total_capital,
            "invested_capital": round(self.invested_capital, 2),
            "cash_reserved": round(self.cash_reserved, 2),
            "cash_weight_pct": round(self.cash_weight_pct, 2),
            "account_currency": self.account_currency,
            "duration_label": self.duration_label,
            "horizon_trading_days": self.horizon_trading_days,
            "assets": [a.__dict__ for a in self.assets],
            "scenarios": {
                "bearish": self.bearish.__dict__,
                "base": self.base.__dict__,
                "bullish": self.bullish.__dict__,
            },
            "portfolio_expected_return_pct": round(self.portfolio_expected_return_pct, 2),
            "portfolio_annualized_volatility_pct": round(self.portfolio_annualized_volatility_pct, 2),
            "portfolio_horizon_volatility_pct": round(self.portfolio_horizon_volatility_pct, 2),
            "estimated_max_drawdown_pct": round(self.estimated_max_drawdown_pct, 2),
            "diversification_benefit_pct": round(self.diversification_benefit_pct, 2),
            "hhi_concentration_index": round(self.hhi_concentration_index, 1),
            "concentration_rating": self.concentration_rating,
            "top_holding_pct": round(self.top_holding_pct, 1),
            "country_exposure": self.country_exposure,
            "sector_exposure": self.sector_exposure,
            "probability_positive_return": round(self.probability_positive_return, 4),
            "probability_loss": round(self.probability_loss, 4),
            "correlation_matrix": self.correlation_matrix,
            "tickers_evaluated": self.tickers_evaluated,
            "risk_factors": self.risk_factors,
            "methodology_notes": self.methodology_notes,
        }


class MultiStockPortfolioSimulator:
    """Simulates portfolio-level return distributions with correlation modeling."""

    def __init__(self, transaction_cost_pct: float = 0.001):
        self.transaction_cost_pct = transaction_cost_pct
        self.forecasting_engine = ReturnForecastingEngine(transaction_cost_pct=transaction_cost_pct)

    def simulate_portfolio(
        self,
        allocations: List[Dict[str, Any]],
        total_capital: Optional[float] = None,
        duration: Union[str, int] = "1m",
        account_currency: str = "INR",
        risk_level: str = "Moderate",
    ) -> PortfolioSimulationResult:
        """Simulate multi-asset portfolio with historical covariance and diversification benefits.
        
        allocations: List of dicts, e.g. [{"ticker": "NVDA", "amount": 20000}, {"ticker": "AAPL", "amount": 15000}]
        """
        if not allocations:
            raise ValueError("At least one stock allocation is required.")

        acc_currency = account_currency.upper()
        trading_days = parse_duration_to_trading_days(duration)
        duration_label = str(duration).capitalize() if isinstance(duration, str) else f"{trading_days} trading sessions"

        # 1. Normalize allocations and total capital
        parsed_allocations: List[AssetAllocationInput] = []
        invested_capital = 0.0

        for item in allocations:
            tick = validate_ticker(item.get("ticker", ""))
            amt = float(item.get("amount", 0.0))
            if amt > 0:
                parsed_allocations.append(AssetAllocationInput(ticker=tick, allocation_amount=amt))
                invested_capital += amt

        if not parsed_allocations:
            raise ValueError("At least one positive allocation amount is required.")

        if total_capital is None or total_capital < invested_capital:
            total_capital = invested_capital

        cash_reserved = max(0.0, total_capital - invested_capital)
        cash_weight = (cash_reserved / total_capital) * 100 if total_capital > 0 else 0.0

        # 2. Fetch market data series for all assets to compute returns & covariance
        ticker_data_map: Dict[str, pd.Series] = {}
        asset_details: List[AllocatedAssetDetail] = []
        single_forecasts: Dict[str, Any] = {}

        for alloc in parsed_allocations:
            t = alloc.ticker
            amt = alloc.allocation_amount
            w_pct = (amt / total_capital) * 100

            # Get quote & company metadata
            quote = get_latest_price(t)
            price = float(quote.get("price", 100.0))
            exc = get_exchange_info(t)
            asset_curr = (quote.get("currency") or exc.currency or "USD").upper()
            fx = get_fx_rate(asset_curr, acc_currency)

            funds = fetch_fundamentals(t)
            name = funds.get("company_name") or quote.get("company_name") or t
            sector = funds.get("sector") or "Global Equities"
            country = funds.get("country") or exc.country or "Global"

            # Single forecast for individual expected return & volatility
            fc = self.forecasting_engine.predict_return_distribution(
                ticker=t,
                investment_amount=amt,
                duration=duration,
                risk_level=risk_level,
                account_currency=acc_currency,
            )
            single_forecasts[t] = fc
            exp_ret = fc.base.return_pct
            ann_vol = fc.expected_volatility_annualized

            asset_details.append(
                AllocatedAssetDetail(
                    ticker=t,
                    company_name=name,
                    exchange=exc.code,
                    country=country,
                    sector=sector,
                    currency=asset_curr,
                    latest_price=price,
                    fx_rate=fx,
                    allocated_amount_account=amt,
                    weight_pct=w_pct,
                    expected_return_pct=exp_ret,
                    annualized_volatility_pct=ann_vol,
                )
            )

            # Daily close price series
            raw_df = fetch_market_data(t, period="2y")
            clean_df = clean_market_data(raw_df)
            ticker_data_map[t] = clean_df["Close"].pct_change().dropna()

        # 3. Construct unified returns dataframe and empirical covariance/correlation
        returns_df = pd.DataFrame(ticker_data_map).dropna()
        tickers = [a.ticker for a in parsed_allocations]
        n_assets = len(tickers)

        if len(returns_df) >= 30 and n_assets > 1:
            cov_matrix_daily = returns_df[tickers].cov().values
            corr_matrix_df = returns_df[tickers].corr()
            corr_dict = corr_matrix_df.round(3).to_dict()
        else:
            # Fallback uncorrelated / moderate default correlation (0.35)
            cov_matrix_daily = np.zeros((n_assets, n_assets))
            corr_dict = {}
            for i, t1 in enumerate(tickers):
                corr_dict[t1] = {}
                v1 = (asset_details[i].annualized_volatility_pct / 100.0) / math.sqrt(252)
                for j, t2 in enumerate(tickers):
                    v2 = (asset_details[j].annualized_volatility_pct / 100.0) / math.sqrt(252)
                    rho = 1.0 if i == j else 0.35
                    cov_matrix_daily[i, j] = rho * v1 * v2
                    corr_dict[t1][t2] = rho

        # 4. Portfolio Variance and Return Calculation
        # Weights normalized across TOTAL capital (including cash reserved with return=0, vol=0)
        invested_weights = np.array([a.allocated_amount_account / total_capital for a in asset_details])
        weighted_returns = sum(
            invested_weights[i] * (asset_details[i].expected_return_pct / 100.0)
            for i in range(n_assets)
        )
        port_expected_return_pct = weighted_returns * 100

        # Portfolio daily variance: w^T * Cov * w
        port_daily_var = float(invested_weights @ cov_matrix_daily @ invested_weights)
        port_daily_vol = math.sqrt(max(1e-8, port_daily_var))
        port_annualized_vol = port_daily_vol * math.sqrt(252) * 100
        port_horizon_vol = port_daily_vol * math.sqrt(trading_days) * 100

        # Diversification benefit: difference between weighted average volatility and portfolio volatility
        weighted_avg_vol = sum(
            (asset_details[i].allocated_amount_account / invested_capital) * asset_details[i].annualized_volatility_pct
            for i in range(n_assets)
        )
        # Scale to match total capital weighting
        scaled_weighted_vol = weighted_avg_vol * (invested_capital / total_capital)
        div_benefit = max(0.0, scaled_weighted_vol - port_annualized_vol)

        # 5. Herfindahl-Hirschman Index (HHI) for Concentration Risk
        # Computed across all capital components (including cash)
        all_weights_pct = [a.weight_pct for a in asset_details]
        if cash_weight > 0:
            all_weights_pct.append(cash_weight)
        hhi = sum(w ** 2 for w in all_weights_pct)

        max_asset_weight = max([a.weight_pct for a in asset_details]) if asset_details else 0.0
        if max_asset_weight > 50 or hhi > 2500:
            conc_rating = "High (Concentrated in single position)"
        elif max_asset_weight > 30 or hhi > 1500:
            conc_rating = "Moderate"
        else:
            conc_rating = "Low (Well Diversified)"

        # 6. Sector and Country Exposure Breakdown
        country_exp: Dict[str, float] = {}
        sector_exp: Dict[str, float] = {}
        for a in asset_details:
            country_exp[a.country] = country_exp.get(a.country, 0.0) + a.weight_pct
            sector_exp[a.sector] = sector_exp.get(a.sector, 0.0) + a.weight_pct
        if cash_weight > 0:
            country_exp["Cash Reserve"] = cash_weight
            sector_exp["Cash Reserve"] = cash_weight

        country_exp = {k: round(v, 1) for k, v in country_exp.items()}
        sector_exp = {k: round(v, 1) for k, v in sector_exp.items()}

        # 7. Maximum Drawdown Estimation from historical returns
        if len(returns_df) >= 30:
            port_daily_series = returns_df[tickers] @ (invested_weights * (total_capital / invested_capital))
            cum_wealth = (1.0 + port_daily_series).cumprod()
            rolling_max = cum_wealth.cummax()
            drawdowns = (cum_wealth - rolling_max) / rolling_max
            max_dd = float(abs(drawdowns.min())) * 100
        else:
            # Empirical 3-sigma estimate scaled by square root of horizon
            max_dd = min(75.0, port_annualized_vol * 1.5)

        # 8. Scenario Projections using portfolio volatility
        horizon_vol_dec = port_horizon_vol / 100.0
        bear_ret = (port_expected_return_pct / 100.0) - (1.645 * horizon_vol_dec)
        base_ret = port_expected_return_pct / 100.0
        bull_ret = (port_expected_return_pct / 100.0) + (1.645 * horizon_vol_dec)

        # Apply transaction costs on invested capital
        effective_cost = invested_capital * (self.transaction_cost_pct * 2)

        def make_port_sc(name: str, label: str, ret: float, desc: str) -> ScenarioOutcome:
            gross_val = (invested_capital * (1.0 + ret)) + cash_reserved
            net_val = max(0.0, gross_val - effective_cost)
            net_pl = net_val - total_capital
            pct = (net_pl / total_capital) * 100 if total_capital > 0 else 0.0
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

        bear_sc = make_port_sc(
            "Bearish",
            "Downside Portfolio Stress (10th percentile)",
            bear_ret,
            f"Adverse market shock where correlated assets drop simultaneously across the {duration_label} horizon.",
        )
        base_sc = make_port_sc(
            "Base",
            "Correlated Base Expectation",
            base_ret,
            f"Central outcome based on asset allocations and historical correlation structure across {duration_label}.",
        )
        bull_sc = make_port_sc(
            "Bullish",
            "Upside Momentum Expansion (90th percentile)",
            bull_ret,
            f"Favourable market expansion where portfolio assets capture positive cross-asset momentum.",
        )

        # Probabilities
        if horizon_vol_dec > 0:
            prob_loss = float(stats.norm.cdf(-base_ret / horizon_vol_dec))
            prob_positive = float(1.0 - prob_loss)
        else:
            prob_loss = 0.5
            prob_positive = 0.5

        risk_factors = [
            f"Concentration Rating: {conc_rating} (HHI: {hhi:.0f}/10,000). Top asset: {asset_details[0].ticker} ({max_asset_weight:.1f}%).",
            f"Estimated historical maximum drawdown for this weighting is {max_dd:.1f}%.",
            f"Cross-asset correlation reduces total portfolio volatility by {div_benefit:.1f}% compared to holding assets in isolation.",
        ]
        if cash_weight > 20:
            risk_factors.append(f"Cash Drag: Holding {cash_weight:.1f}% in uninvested cash reduces upside participation during bull markets.")

        methodology_notes = [
            f"Multi-Asset Covariance: Portfolio variance computed using Markowitz framework (w^T * Cov * w).",
            f"Sample size: {len(returns_df)} synchronized trading sessions across {n_assets} assets.",
            f"Simulated transaction fees of {self.transaction_cost_pct*100:.1f}% deducted ({format_currency_amount(effective_cost, acc_currency)}).",
        ]

        return PortfolioSimulationResult(
            total_capital=total_capital,
            invested_capital=invested_capital,
            cash_reserved=cash_reserved,
            cash_weight_pct=cash_weight,
            account_currency=acc_currency,
            duration_label=duration_label,
            horizon_trading_days=trading_days,
            assets=asset_details,
            bearish=bear_sc,
            base=base_sc,
            bullish=bull_sc,
            portfolio_expected_return_pct=port_expected_return_pct,
            portfolio_annualized_volatility_pct=port_annualized_vol,
            portfolio_horizon_volatility_pct=port_horizon_vol,
            estimated_max_drawdown_pct=max_dd,
            diversification_benefit_pct=div_benefit,
            hhi_concentration_index=hhi,
            concentration_rating=conc_rating,
            top_holding_pct=max_asset_weight,
            country_exposure=country_exp,
            sector_exposure=sector_exp,
            probability_positive_return=prob_positive,
            probability_loss=prob_loss,
            correlation_matrix=corr_dict,
            tickers_evaluated=tickers,
            risk_factors=risk_factors,
            methodology_notes=methodology_notes,
        )
