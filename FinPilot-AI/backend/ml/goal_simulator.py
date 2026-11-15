"""FinPilot AI — Investment Goal & Return Hurdle Simulator.

Calculates exact compounding requirements, statistical feasibility, and hurdle rates
for financial targets (e.g. ₹10,000 to ₹1,00,000) across diverse time horizons.
Never creates false hope: honestly diagnoses extreme or statistically impossible targets.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union

import numpy as np
from scipy import stats

from backend.data.global_exchanges import format_currency_amount
from backend.ml.return_forecasting import parse_duration_to_trading_days

log = logging.getLogger(__name__)


@dataclass
class GoalHorizonFeasibility:
    horizon_label: str
    calendar_duration: str
    trading_sessions: int
    required_total_return_pct: float
    required_daily_compounded_return_pct: float
    required_weekly_compounded_return_pct: float
    required_monthly_compounded_return_pct: float
    probability_of_reaching_target: float
    feasibility_status: str  # "Statistically Extreme", "Highly Aggressive", "Moderate / Achievable", "Realistic"
    historical_benchmark_comparison: str
    risk_verdict: str


@dataclass
class GoalSimulationResult:
    starting_capital: float
    target_amount: float
    selected_duration: str
    currency: str
    required_absolute_gain: float
    required_total_return_pct: float
    multiple_factor: float

    # Selected horizon detailed metrics
    selected_horizon: GoalHorizonFeasibility

    # Comparison across all standard horizons (1w, 2w, 1m, 3m, 6m, 1y)
    all_horizons: List[GoalHorizonFeasibility]

    # Transparency and reality check
    reality_check_summary: str
    is_target_extreme: bool
    extreme_warning: Optional[str]
    honest_advice: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "starting_capital": self.starting_capital,
            "target_amount": self.target_amount,
            "selected_duration": self.selected_duration,
            "currency": self.currency,
            "required_absolute_gain": round(self.required_absolute_gain, 2),
            "required_total_return_pct": round(self.required_total_return_pct, 2),
            "multiple_factor": round(self.multiple_factor, 2),
            "selected_horizon": self.selected_horizon.__dict__,
            "all_horizons": [h.__dict__ for h in self.all_horizons],
            "reality_check_summary": self.reality_check_summary,
            "is_target_extreme": self.is_target_extreme,
            "extreme_warning": self.extreme_warning,
            "honest_advice": self.honest_advice,
        }


class InvestmentGoalSimulator:
    """Evaluates the mathematical and empirical viability of financial targets."""

    STANDARD_HORIZONS = [
        ("1 week", 5, "1 week"),
        ("2 weeks", 10, "2 weeks"),
        ("1 month", 21, "1 month"),
        ("3 months", 63, "3 months"),
        ("6 months", 126, "6 months"),
        ("1 year", 252, "1 year"),
    ]

    # Benchmark market context for reality checks (long-term annual equity return ~12-15% in INR, ~10% in USD)
    EQUITY_BENCHMARK_ANNUAL_RETURN = 0.13  # 13% CAGR benchmark
    EQUITY_BENCHMARK_ANNUAL_VOL = 0.16     # 16% annualized volatility

    @classmethod
    def simulate_goal(
        cls,
        starting_capital: float,
        target_amount: float,
        time_available: Union[str, int] = "1 month",
        currency: str = "INR",
        asset_annual_volatility: Optional[float] = None,
        asset_expected_drift: Optional[float] = None,
    ) -> GoalSimulationResult:
        """Calculate required compounding hurdle and evaluate mathematical viability."""
        if starting_capital <= 0:
            raise ValueError("Starting capital must be greater than zero.")
        if target_amount <= starting_capital:
            raise ValueError("Target amount must be strictly greater than starting capital.")

        currency = currency.upper()
        gain_needed = target_amount - starting_capital
        total_return_req = (gain_needed / starting_capital) * 100
        multiple = target_amount / starting_capital

        # Volatility & drift assumptions: use asset metrics if provided, else institutional equity benchmark
        sigma_annual = (asset_annual_volatility / 100.0) if asset_annual_volatility else cls.EQUITY_BENCHMARK_ANNUAL_VOL
        mu_annual = asset_expected_drift if asset_expected_drift is not None else cls.EQUITY_BENCHMARK_ANNUAL_RETURN
        sigma_daily = sigma_annual / math.sqrt(252)
        mu_daily = mu_annual / 252

        # Evaluate each standard horizon
        horizon_results: List[GoalHorizonFeasibility] = []
        for label, trading_days, cal_dur in cls.STANDARD_HORIZONS:
            h_feas = cls._calculate_horizon_metrics(
                starting_capital=starting_capital,
                target_amount=target_amount,
                multiple=multiple,
                total_return_pct=total_return_req,
                trading_days=trading_days,
                horizon_label=label,
                calendar_duration=cal_dur,
                mu_daily=mu_daily,
                sigma_daily=sigma_daily,
                currency=currency,
            )
            horizon_results.append(h_feas)

        # Selected horizon lookup
        sel_days = parse_duration_to_trading_days(time_available)
        sel_label = str(time_available).capitalize()
        # Find exact match or construct custom horizon
        selected_feasibility = next(
            (h for h in horizon_results if h.trading_sessions == sel_days),
            None,
        )
        if not selected_feasibility:
            selected_feasibility = cls._calculate_horizon_metrics(
                starting_capital=starting_capital,
                target_amount=target_amount,
                multiple=multiple,
                total_return_pct=total_return_req,
                trading_days=sel_days,
                horizon_label=sel_label,
                calendar_duration=sel_label,
                mu_daily=mu_daily,
                sigma_daily=sigma_daily,
                currency=currency,
            )

        # Extreme warning diagnosis
        is_extreme = selected_feasibility.feasibility_status in ("Statistically Extreme", "Highly Aggressive")
        extreme_warning = None
        if is_extreme:
            extreme_warning = (
                f"🚨 STATISTICALLY EXTREME GOAL: Turning {format_currency_amount(starting_capital, currency)} "
                f"into {format_currency_amount(target_amount, currency)} ({multiple:.1f}x or +{total_return_req:,.0f}%) "
                f"in {selected_feasibility.calendar_duration} requires a compounded return of "
                f"+{selected_feasibility.required_daily_compounded_return_pct:.2f}% per single trading day. "
                f"No legitimate investment vehicle or institutional algorithm reliably provides this return "
                f"without exposing the investor to a virtual 100% risk of total capital wipeout."
            )

        honest_advice = cls._formulate_honest_advice(
            starting_capital=starting_capital,
            target_amount=target_amount,
            multiple=multiple,
            total_return_req=total_return_req,
            selected_h=selected_feasibility,
            currency=currency,
        )

        reality_summary = (
            f"Achieving {format_currency_amount(target_amount, currency)} from {format_currency_amount(starting_capital, currency)} "
            f"requires a +{total_return_req:,.1f}% gain. Over {selected_feasibility.calendar_duration}, "
            f"the required compounded rate is {selected_feasibility.required_daily_compounded_return_pct:.2f}% per trading session. "
            f"Verdict: {selected_feasibility.feasibility_status}."
        )

        return GoalSimulationResult(
            starting_capital=starting_capital,
            target_amount=target_amount,
            selected_duration=str(time_available),
            currency=currency,
            required_absolute_gain=gain_needed,
            required_total_return_pct=total_return_req,
            multiple_factor=multiple,
            selected_horizon=selected_feasibility,
            all_horizons=horizon_results,
            reality_check_summary=reality_summary,
            is_target_extreme=is_extreme,
            extreme_warning=extreme_warning,
            honest_advice=honest_advice,
        )

    @classmethod
    def _calculate_horizon_metrics(
        cls,
        starting_capital: float,
        target_amount: float,
        multiple: float,
        total_return_pct: float,
        trading_days: int,
        horizon_label: str,
        calendar_duration: str,
        mu_daily: float,
        sigma_daily: float,
        currency: str,
    ) -> GoalHorizonFeasibility:
        """Calculate exact daily, weekly, and monthly geometric compounding hurdles."""
        # Compound daily rate r_d: (1 + r_d)^trading_days = multiple
        # => r_d = multiple^(1 / trading_days) - 1
        daily_req = (multiple ** (1.0 / trading_days)) - 1.0
        daily_req_pct = daily_req * 100

        # Weekly compounding rate (assuming 5 trading days / week)
        weeks = max(0.2, trading_days / 5.0)
        weekly_req = (multiple ** (1.0 / weeks)) - 1.0
        weekly_req_pct = weekly_req * 100

        # Monthly compounding rate (assuming 21 trading days / month)
        months = max(0.05, trading_days / 21.0)
        monthly_req = (multiple ** (1.0 / months)) - 1.0
        monthly_req_pct = monthly_req * 100

        # Statistical probability under Geometric Brownian Motion with Fat Tails (Student-t df=5)
        # Log return required = ln(multiple)
        log_ret_req = math.log(multiple)
        mu_h = (mu_daily - 0.5 * (sigma_daily ** 2)) * trading_days
        sigma_h = sigma_daily * math.sqrt(trading_days)

        if sigma_h > 0:
            z_score = (log_ret_req - mu_h) / sigma_h
            # Probability of reaching or exceeding target at horizon end
            # Using Student-t distribution with df=5 for heavy tails
            prob_target = float(1.0 - stats.t.cdf(z_score, df=5))
            # Probability clamp: never give exactly 0.0 or 1.0 in financial statistics
            prob_target = max(0.0001, min(0.9999, prob_target))
        else:
            prob_target = 0.0001

        # Classify feasibility
        if daily_req_pct > 5.0 or prob_target < 0.01:
            status = "Statistically Extreme"
            verdict = "Statistically near-impossible via public equities; resembles lottery odds."
            bench_comp = "Exceeds historical maximum single-stock sustained compounding streaks."
        elif daily_req_pct > 1.5 or prob_target < 0.08:
            status = "Highly Aggressive"
            verdict = "Extremely high risk; requires extraordinary continuous directional rallies."
            bench_comp = "Roughly 10x-20x the standard institutional benchmark pace."
        elif daily_req_pct > 0.40 or prob_target < 0.25:
            status = "Moderate / Aggressive"
            verdict = "Challenging target; requires strong bull momentum and high risk tolerance."
            bench_comp = "Comparable to top-decile growth stock breakouts."
        else:
            status = "Realistic / Achievable"
            verdict = "Realistic target consistent with disciplined equity investing."
            bench_comp = "Aligns well with diversified historical market returns over time."

        return GoalHorizonFeasibility(
            horizon_label=horizon_label,
            calendar_duration=calendar_duration,
            trading_sessions=trading_days,
            required_total_return_pct=round(total_return_pct, 2),
            required_daily_compounded_return_pct=round(daily_req_pct, 2),
            required_weekly_compounded_return_pct=round(weekly_req_pct, 2),
            required_monthly_compounded_return_pct=round(monthly_req_pct, 2),
            probability_of_reaching_target=round(prob_target, 4),
            feasibility_status=status,
            historical_benchmark_comparison=bench_comp,
            risk_verdict=verdict,
        )

    @classmethod
    def _formulate_honest_advice(
        cls,
        starting_capital: float,
        target_amount: float,
        multiple: float,
        total_return_req: float,
        selected_h: GoalHorizonFeasibility,
        currency: str,
    ) -> str:
        """Generate compassionate, rigorous institutional guidance."""
        if selected_h.feasibility_status == "Statistically Extreme":
            return (
                f"Turning {format_currency_amount(starting_capital, currency)} into "
                f"{format_currency_amount(target_amount, currency)} is a {multiple:.0f}x capital increase (+{total_return_req:,.0f}%). "
                f"In financial markets, pursuing a +{selected_h.required_daily_compounded_return_pct:.2f}% gain each trading day "
                f"inevitably requires leverage, speculative options, or concentrated micro-caps where the risk of total loss is nearly 100%. "
                f"A safer pathway is systematic monthly accumulation (SIP) and extending the horizon to allow authentic compound interest to work."
            )
        elif selected_h.feasibility_status == "Highly Aggressive":
            return (
                f"Reaching {format_currency_amount(target_amount, currency)} in {selected_h.calendar_duration} "
                f"requires compounding at +{selected_h.required_weekly_compounded_return_pct:.1f}% every week without major drawdowns. "
                f"While individual outlier stocks occasionally produce such runs during bull markets, expecting consistent performance "
                f"carries severe drawdown risk. Consider diversifying across 3–5 high-conviction global leaders."
            )
        else:
            return (
                f"This target requires a +{total_return_req:.1f}% overall gain, which represents a balanced, achievable objective "
                f"over {selected_h.calendar_duration} with quality global companies. Maintain strict stop-loss rules and monitor earnings updates."
            )
