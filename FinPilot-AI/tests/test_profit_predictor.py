"""FinPilot AI — Acceptance Test Suite for AI Profit Predictor & Goal Simulator.

Validates all 12 mandatory acceptance criteria:
1. ₹10,000 investment for one week.
2. ₹10,000 investment for one month.
3. ₹50,000 investment for three months.
4. ₹1,00,000 investment for one year.
5. ₹10,000 target amount of ₹1,00,000 within one week (Extreme hurdle diagnosis).
6. ₹10,000 target amount of ₹1,00,000 within one month (Statistically extreme diagnosis).
7. Multiple global company comparison.
8. Multi-company portfolio simulation.
9. Bearish market scenario (Downside calibration < Base).
10. Bullish market scenario (Upside calibration > Base).
11. Missing financial data handling (Safeguard without fabrication).
12. Missing AI credentials (Local offline fallback resilience).
"""

import math
import pytest
from backend.ml.return_forecasting import (
    ReturnForecastingEngine,
    parse_duration_to_trading_days,
)
from backend.ml.goal_simulator import InvestmentGoalSimulator
from backend.ml.portfolio_simulator import MultiStockPortfolioSimulator
from backend.assistant.ai_assistant import FinPilotAIAssistant


@pytest.fixture
def forecasting_engine():
    return ReturnForecastingEngine(transaction_cost_pct=0.001)


@pytest.fixture
def portfolio_simulator():
    return MultiStockPortfolioSimulator(transaction_cost_pct=0.001)


# Scenario 1: ₹10,000 investment for one week
def test_scenario_1_10k_one_week(forecasting_engine):
    res = forecasting_engine.predict_return_distribution(
        ticker="NVDA",
        investment_amount=10000.0,
        duration="1w",
        account_currency="INR",
    )
    assert res.investment_amount == 10000.0
    assert res.horizon_trading_days == 5
    assert res.bearish.ending_value < res.base.ending_value
    assert res.base.ending_value < res.bullish.ending_value
    assert 0.0 <= res.probability_positive_return <= 1.0
    assert 0.0 <= res.probability_loss <= 1.0
    assert res.simulated_transaction_cost_pct > 0.0
    assert len(res.risk_factors) > 0


# Scenario 2: ₹10,000 investment for one month
def test_scenario_2_10k_one_month(forecasting_engine):
    res = forecasting_engine.predict_return_distribution(
        ticker="NVDA",
        investment_amount=10000.0,
        duration="1m",
        account_currency="INR",
    )
    assert res.investment_amount == 10000.0
    assert res.horizon_trading_days == 21
    assert res.bearish.return_pct < res.base.return_pct
    assert res.base.return_pct < res.bullish.return_pct
    assert res.net_cost_deducted > 0.0
    # Bearish scenario reflects loss or significantly lower return
    assert res.bearish.profit_loss < res.base.profit_loss


# Scenario 3: ₹50,000 investment for three months
def test_scenario_3_50k_three_months(forecasting_engine):
    res = forecasting_engine.predict_return_distribution(
        ticker="AAPL",
        investment_amount=50000.0,
        duration="3m",
        account_currency="INR",
    )
    assert res.investment_amount == 50000.0
    assert res.horizon_trading_days == 63
    assert res.bearish.ending_value < res.bullish.ending_value
    assert res.expected_volatility_annualized > 0.0
    assert res.forecast_uncertainty_pct > 0.0


# Scenario 4: ₹1,00,000 investment for one year
def test_scenario_4_100k_one_year(forecasting_engine):
    res = forecasting_engine.predict_return_distribution(
        ticker="MSFT",
        investment_amount=100000.0,
        duration="1y",
        account_currency="INR",
    )
    assert res.investment_amount == 100000.0
    assert res.horizon_trading_days == 252
    assert res.bearish.ending_value < res.base.ending_value < res.bullish.ending_value
    # 1 year horizon should note macro risks
    assert any("macro" in rf.lower() or "horizon" in rf.lower() for rf in res.risk_factors)


# Scenario 5: ₹10,000 target amount of ₹1,00,000 within one week (extreme hurdle)
def test_scenario_5_goal_10k_to_100k_one_week():
    res = InvestmentGoalSimulator.simulate_goal(
        starting_capital=10000.0,
        target_amount=100000.0,
        time_available="1 week",
        currency="INR",
    )
    assert res.multiple_factor == 10.0
    assert res.required_total_return_pct == 900.0
    assert res.is_target_extreme is True
    assert res.extreme_warning is not None
    # Turning 10k into 100k in 5 trading days requires > 50% compounding daily!
    assert res.selected_horizon.required_daily_compounded_return_pct > 50.0
    assert res.selected_horizon.feasibility_status == "Statistically Extreme"
    assert res.selected_horizon.probability_of_reaching_target < 0.05


# Scenario 6: ₹10,000 target amount of ₹1,00,000 within one month (extreme hurdle)
def test_scenario_6_goal_10k_to_100k_one_month():
    res = InvestmentGoalSimulator.simulate_goal(
        starting_capital=10000.0,
        target_amount=100000.0,
        time_available="1 month",
        currency="INR",
    )
    assert res.multiple_factor == 10.0
    assert res.selected_horizon.trading_sessions == 21
    # Turning 10k into 100k in 21 days requires ~11.59% compounding daily
    assert 10.0 < res.selected_horizon.required_daily_compounded_return_pct < 15.0
    assert res.is_target_extreme is True
    assert "extreme" in res.selected_horizon.feasibility_status.lower()


# Scenario 7: Multiple global company comparison
def test_scenario_7_multiple_company_comparison(forecasting_engine):
    tickers = ["NVDA", "AAPL", "7203.T", "SIE.DE"]
    results = {}
    for t in tickers:
        r = forecasting_engine.predict_return_distribution(
            ticker=t,
            investment_amount=10000.0,
            duration="1m",
            account_currency="INR",
        )
        results[t] = r
        assert r.ticker == t
        assert r.bearish.ending_value < r.bullish.ending_value
        assert r.current_price > 0.0

    # Ensure each asset has distinct volatility/returns based on real asset history
    volatilities = [r.expected_volatility_annualized for r in results.values()]
    assert len(set(round(v, 1) for v in volatilities)) > 1


# Scenario 8: Multi-company portfolio simulation
def test_scenario_8_portfolio_simulation(portfolio_simulator):
    allocations = [
        {"ticker": "NVDA", "amount": 20000.0},
        {"ticker": "AAPL", "amount": 15000.0},
        {"ticker": "RELIANCE.NS", "amount": 10000.0},
    ]
    res = portfolio_simulator.simulate_portfolio(
        allocations=allocations,
        total_capital=50000.0,
        duration="1m",
        account_currency="INR",
    )
    assert res.total_capital == 50000.0
    assert res.invested_capital == 45000.0
    assert res.cash_reserved == 5000.0
    assert res.cash_weight_pct == 10.0
    assert res.bearish.ending_value < res.base.ending_value < res.bullish.ending_value
    assert res.hhi_concentration_index > 0.0
    assert len(res.country_exposure) >= 2
    assert "NVDA" in res.correlation_matrix


# Scenario 9: Bearish market scenario
def test_scenario_9_bearish_scenario(forecasting_engine):
    res = forecasting_engine.predict_return_distribution("NVDA", 10000.0, "1m")
    # Bearish return must be strictly worse than base
    assert res.bearish.return_pct < res.base.return_pct
    assert res.bearish.profit_loss < 0.0 or res.bearish.profit_loss < res.base.profit_loss
    assert res.bearish.ending_value < res.investment_amount or res.bearish.ending_value < res.base.ending_value


# Scenario 10: Bullish market scenario
def test_scenario_10_bullish_scenario(forecasting_engine):
    res = forecasting_engine.predict_return_distribution("NVDA", 10000.0, "1m")
    # Bullish return must be strictly better than base
    assert res.bullish.return_pct > res.base.return_pct
    assert res.bullish.profit_loss > res.base.profit_loss
    assert res.bullish.ending_value > res.base.ending_value


# Scenario 11: Missing financial data safeguard
def test_scenario_11_missing_financial_data(forecasting_engine):
    # Pass an unknown symbol with zero data
    res = forecasting_engine._build_insufficient_data_result(
        ticker="UNKNOWN999",
        company_name="Unknown Entity",
        investment_amount=10000.0,
        duration_label="1 month",
        trading_days=21,
        current_price=100.0,
        asset_currency="USD",
        acc_currency="INR",
        fx_rate=86.0,
        target_amount=None,
        risk_level="Moderate",
        quote_timestamp="2026-11-15T00:00:00Z",
    )
    assert res.is_insufficient_data is True
    assert res.bearish.ending_value == 10000.0  # Safe fallback without fabricated loss/gain
    assert "prohibits" in res.methodology_notes[0] or "safeguard" in res.model_name.lower()


# Scenario 12: Missing AI credentials (offline assistant fallback)
def test_scenario_12_missing_ai_credentials_assistant():
    assistant = FinPilotAIAssistant()
    # Ensure offline rule-based knowledge handles goal and prediction questions seamlessly
    resp_goal = assistant._build_offline_response(
        "I want to reach 1 lakh from 10,000 in 1 month",
        is_beginner=True,
        company=None,
        portfolio={"account_currency": "INR", "available_cash": 10000.0},
    )
    assert "Compounding" in resp_goal or "Hurdle" in resp_goal or "Goal" in resp_goal
    assert "Extreme" in resp_goal or "Daily" in resp_goal

    resp_profit = assistant._build_offline_response(
        "What could happen if I invest 5000 in NVIDIA?",
        is_beginner=True,
        company=None,
        portfolio={"account_currency": "INR", "available_cash": 50000.0},
    )
    assert "Bearish" in resp_profit
    assert "Base" in resp_profit
    assert "Bullish" in resp_profit
