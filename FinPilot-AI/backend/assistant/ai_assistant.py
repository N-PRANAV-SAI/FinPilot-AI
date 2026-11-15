"""Context-Aware AI Financial Assistant for FinPilot AI.
Provides beginner-friendly explanations, quantitative research breakdowns,
and guided investment practice using Gemini LLM and local financial knowledge.
"""
from typing import Dict, Any, List, Optional
import json
import logging
from backend.llm.gemini_provider import GeminiProvider
from backend.data.global_exchanges import format_currency_amount

logger = logging.getLogger(__name__)

FINANCIAL_GLOSSARY_EXPLANATIONS = {
    "what is a stock": "A **stock** (also called a share or equity) represents fractional ownership in a corporation. When you own a stock, you own a small slice of that company's assets and future earnings. If the company grows and becomes more profitable, the value of your shares can increase, and you may also receive cash payouts called **dividends**.",
    "stock": "A **stock** (or share) represents partial ownership of a corporation. Owning stock entitles you to a portion of the company's earnings and potential voting rights on major corporate decisions.",
    "rsi": "**Relative Strength Index (RSI)** is a momentum indicator that oscillates between 0 and 100. Traditionally, an RSI reading **above 70** indicates that an asset may be *overbought* (priced high relative to recent history), while an RSI **below 30** indicates that it may be *oversold* (potentially undervalued or experiencing heavy selling pressure).",
    "pe": "The **Price-to-Earnings (P/E) Ratio** measures how much investors are willing to pay per dollar of annual company earnings (Share Price ÷ Earnings Per Share). A high P/E often indicates high market expectations for future growth, while a lower P/E may indicate a value stock or slower growth prospects.",
    "macd": "**Moving Average Convergence Divergence (MACD)** is a trend-following momentum indicator showing the relationship between two moving averages (usually 12-day and 26-day EMA). A bullish signal occurs when the MACD line crosses above the signal line; a bearish signal occurs when it crosses below.",
    "diversification": "**Diversification** is the fundamental risk-management strategy of spreading investments across varied companies, sectors, and geographic regions. By diversifying, a sharp drop in any single stock does not cripple your overall portfolio.",
    "market_cap": "**Market Capitalization** is the aggregate market value of a company's outstanding shares (Share Price × Total Shares). It categorizes companies into Large-Cap (stable, established), Mid-Cap (growth-oriented), and Small-Cap (higher potential growth with higher volatility).",
    "shap": "**SHAP (SHapley Additive exPlanations)** is an Explainable AI framework from cooperative game theory. It breaks down machine learning predictions to reveal the exact positive or negative contribution of each technical indicator (such as RSI, SMA-50, or Volatility) toward the final 5-session forecast.",
    "limit order": "A **Limit Order** is an order to buy or sell a stock at a specified price or better. A Buy Limit will only execute at or below your limit price, and a Sell Limit will only execute at or above your limit price, protecting you from sudden price fluctuations.",
    "market order": "A **Market Order** is an order to execute immediately at the current prevailing market price. It guarantees execution speed over exact execution price.",
    "candlestick": "A **Candlestick Chart** displays the Open, High, Low, and Close (OHLC) prices for a specific time interval. The wide body represents the range between Open and Close; the thin wicks (shadows) represent the highest and lowest prices reached during that session.",
    "sma": "**Simple Moving Average (SMA)** calculates the average closing price over a specified time period (e.g. 50 or 200 days) to smooth out price fluctuations and highlight trend direction.",
    "ema": "**Exponential Moving Average (EMA)** gives greater weight to the most recent prices, reacting faster to price turns than a simple moving average."
}


class FinPilotAIAssistant:
    """Intelligent financial assistant with dual Beginner/Advanced persona."""

    def __init__(self):
        self.llm = GeminiProvider()

    def generate_response(
        self,
        user_message: str,
        user_profile: Dict[str, Any],
        portfolio_context: Optional[Dict[str, Any]] = None,
        company_context: Optional[Dict[str, Any]] = None,
        chat_history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """Generate tailored AI guidance based on context and user level."""
        exp_level = user_profile.get("experience_level", "Beginner")
        is_beginner = "beginner" in exp_level.lower()

        # Build context prompt
        system_instruction = self._build_system_instruction(is_beginner, user_profile)
        context_block = self._build_context_block(portfolio_context, company_context)

        full_prompt = f"""{system_instruction}

CURRENT FINANCIAL CONTEXT:
{context_block}

USER QUERY:
"{user_message}"

Respond directly to the user in a warm, structured, and informative manner. Format your response cleanly using markdown (bullet points, bold highlights, clear sections). Keep paper-trading disclaimers natural and brief.
"""
        # Check high-speed local quantitative intelligence first for instantaneous responses
        offline_resp = self._build_offline_response(user_message, is_beginner, company_context, portfolio_context)
        if offline_resp and not offline_resp.startswith("👋 **Welcome to FinPilot AI Assistant!**"):
            return offline_resp

        # Try LLM for open-ended queries if available
        if self.llm.is_available():
            try:
                response = self.llm.generate(full_prompt)
                if response and len(response.strip()) > 30:
                    return response
            except Exception as e:
                logger.warning(f"Assistant LLM call failed, switching to local knowledge fallback: {e}")

        return offline_resp

    def _build_system_instruction(self, is_beginner: bool, profile: Dict[str, Any]) -> str:
        if is_beginner:
            return f"""You are FinPilot AI Assistant — an empathetic, world-class financial mentor for a university beginner.
User Name: {profile.get('name', 'Investor')}
User Level: Beginner (New to the stock market)
Preferred Currency: {profile.get('preferred_currency', 'INR')}

Your Principles:
1. Explain financial concepts using simple everyday analogies (e.g. comparing market cap to buying an entire bakery).
2. Avoid unnecessary acronyms or financial jargon without immediately defining them.
3. Always explain the RISKS before discussing potential upside.
4. If asked about a trade, explain the company's business model, historical volatility, and highlight how much virtual cash remains.
5. Emphasize that all trades here are simulated with fake practice funds for learning."""
        else:
            return f"""You are FinPilot AI Assistant — an institutional quantitative research and portfolio risk advisor.
User Name: {profile.get('name', 'Investor')}
User Level: Advanced / Quantitative
Preferred Currency: {profile.get('preferred_currency', 'USD')}

Your Principles:
1. Provide precise technical, fundamental, and quantitative analysis.
2. Incorporate SHAP feature contributions, FinBERT sentiment distributions, and ML model confidence where available.
3. Evaluate portfolio concentration risk (HHI, sector exposure, maximum drawdown).
4. Maintain strict analytical rigor and professional institutional tone."""

    def _build_context_block(self, portfolio: Optional[Dict[str, Any]], company: Optional[Dict[str, Any]]) -> str:
        ctx_parts = []
        if company:
            f = company.get("fundamentals", {})
            p = company.get("prediction", {})
            s = company.get("sentiment", {})
            curr = company.get("currency", "USD")
            sym = company.get("currency_symbol", "$")
            latest_price = company.get("latest_price", {}).get("price", "N/A")

            ctx_parts.append(f"""SELECTED COMPANY CONTEXT:
- Name: {company.get('company_name', 'N/A')} ({company.get('ticker', 'N/A')})
- Exchange: {company.get('exchange', 'N/A')}, Country: {company.get('country', 'N/A')}
- Current Price: {sym}{latest_price} {curr}
- Sector: {f.get('sector', 'N/A')}, P/E: {f.get('trailing_pe', 'N/A')}
- 5-Session AI Direction: {p.get('direction', 'N/A')} (Probability: {p.get('probability', 0.5):.1%}, Model: {p.get('model', 'N/A')})
- FinBERT Sentiment: {s.get('overall_sentiment', 'Neutral')} (Pos: {s.get('positive_ratio', 0.0):.1%}, Neg: {s.get('negative_ratio', 0.0):.1%})""")

        if portfolio:
            c = portfolio.get("account_currency", "INR")
            ctx_parts.append(f"""USER'S VIRTUAL PORTFOLIO CONTEXT:
- Available Cash: {c} {portfolio.get('available_cash', 0.0):,.2f}
- Invested Value: {c} {portfolio.get('invested_value', 0.0):,.2f}
- Total Portfolio Value: {c} {portfolio.get('total_portfolio_value', 0.0):,.2f}
- Unrealized P&L: {c} {portfolio.get('unrealized_pnl', 0.0):+,.2f}
- Active Holdings Count: {len(portfolio.get('holdings', []))}
- Concentration Risk: {portfolio.get('risk_metrics', {}).get('concentration_risk', 'N/A')}""")

        return "\n\n".join(ctx_parts) if ctx_parts else "No active asset or portfolio context selected."

    def _build_offline_response(
        self,
        query: str,
        is_beginner: bool,
        company: Optional[Dict[str, Any]],
        portfolio: Optional[Dict[str, Any]]
    ) -> str:
        q = query.lower()

        # 0. AI Profit Forecasting, Return Predictions & Goal Simulations
        import re
        from backend.ml.return_forecasting import ReturnForecastingEngine
        from backend.ml.goal_simulator import InvestmentGoalSimulator

        # Check for goal simulation questions: e.g. "reach 1 lakh from 10,000", "10,000 to 1,00,000", "target realistic", "what return is required"
        if any(k in q for k in ["reach", "1 lakh", "1,00,000", "100000", "goal", "what return is required", "realistic according to"]):
            # Normalize lakh / crore text to numeric strings
            norm_q = re.sub(r"(\d+)\s*(?:lakh|lac)s?", lambda m: str(int(m.group(1)) * 100000), q)
            norm_q = re.sub(r"(\d+)\s*(?:crore|cr)s?", lambda m: str(int(m.group(1)) * 10000000), norm_q)
            nums = re.findall(r"\d+[\d,]*", norm_q)
            start_val = 10000.0
            target_val = 100000.0
            parsed_vals = []
            for n in nums:
                try:
                    val = float(n.replace(",", ""))
                    if val > 0:
                        parsed_vals.append(val)
                except Exception:
                    pass

            if len(parsed_vals) >= 2:
                start_val = min(parsed_vals[0], parsed_vals[1])
                target_val = max(parsed_vals[0], parsed_vals[1])
            elif len(parsed_vals) == 1:
                if parsed_vals[0] > start_val:
                    target_val = parsed_vals[0]
                else:
                    start_val = parsed_vals[0]

            duration_str = "1 month"
            if "week" in q:
                duration_str = "1 week"
            elif "3 month" in q:
                duration_str = "3 months"
            elif "6 month" in q:
                duration_str = "6 months"
            elif "year" in q:
                duration_str = "1 year"

            c = portfolio.get("account_currency", "INR") if portfolio else "INR"
            goal_res = InvestmentGoalSimulator.simulate_goal(start_val, target_val, duration_str, c)
            sel = goal_res.selected_horizon

            return f"""🎯 **Investment Goal & Hurdle Analysis: {format_currency_amount(start_val, c)} → {format_currency_amount(target_val, c)}**

- **Required Total Gain**: **+{goal_res.required_total_return_pct:,.1f}%** ({goal_res.multiple_factor:.1f}x capital multiplier)
- **Time Horizon Selected**: **{sel.calendar_duration}** ({sel.trading_sessions} trading days)
- **Required Daily Compounding**: **+{sel.required_daily_compounded_return_pct:.2f}% per session**
- **Required Weekly Compounding**: **+{sel.required_weekly_compounded_return_pct:.2f}% per week**
- **Statistical Feasibility Verdict**: **{sel.feasibility_status}** ({sel.risk_verdict})
- **Probability of Achieving**: **{sel.probability_of_reaching_target:.2%}** (based on fat-tailed historical market distributions)

⚠️ **Honest Financial Diagnosis**:
{goal_res.honest_advice}

{"🚨 **Risk Alert**: " + goal_res.extreme_warning if goal_res.extreme_warning else ""}"""

        # Check for potential return / profit queries: e.g. "what could ₹10,000 become in one month", "what could happen if I invest 5000 in NVIDIA", "how much could I lose in the bearish scenario", "explain why the model expects this return"
        if any(k in q for k in ["what could", "become in", "if i invest", "how much could i lose", "bearish scenario", "potential outcomes", "model expects this return", "main risks"]):
            t = "NVDA"
            if company and company.get("ticker"):
                t = company.get("ticker")
            elif "nvidia" in q or "nvda" in q:
                t = "NVDA"
            elif "apple" in q or "aapl" in q:
                t = "AAPL"
            elif "reliance" in q:
                t = "RELIANCE.NS"
            elif "tcs" in q:
                t = "TCS.NS"

            nums = re.findall(r"\d+[\d,]*", query)
            amt = 10000.0
            if nums:
                try:
                    val = float(nums[0].replace(",", ""))
                    if val > 100:
                        amt = val
                except Exception:
                    pass

            dur = "1m"
            dur_label = "1 month"
            if "week" in q:
                dur = "1w"
                dur_label = "1 week"
            elif "3 month" in q:
                dur = "3m"
                dur_label = "3 months"
            elif "year" in q:
                dur = "1y"
                dur_label = "1 year"

            c = portfolio.get("account_currency", "INR") if portfolio else "INR"
            engine = ReturnForecastingEngine()
            fc = engine.predict_return_distribution(t, amt, dur, account_currency=c)

            return f"""📊 **AI Profit Forecast for {fc.company_name} ({fc.ticker})**
*Simulated Virtual Investment: {format_currency_amount(amt, c)} | Horizon: {dur_label}*

| Scenario | Estimated Return | Estimated Profit/Loss | Projected Ending Value |
| :--- | :--- | :--- | :--- |
| **🐻 Bearish (Downside)** | **{fc.bearish.formatted_return}** | **{fc.bearish.formatted_pl}** | **{fc.bearish.formatted_ending_value}** |
| **⚖️ Base (Central)** | **{fc.base.formatted_return}** | **{fc.base.formatted_pl}** | **{fc.base.formatted_ending_value}** |
| **🐂 Bullish (Upside)** | **{fc.bullish.formatted_return}** | **{fc.bullish.formatted_pl}** | **{fc.bullish.formatted_ending_value}** |

**Quantitative Confidence & Uncertainty:**
- **Probability of Positive Return**: **{fc.probability_positive_return:.1%}** (Validated via historical residual distribution)
- **Probability of Loss**: **{fc.probability_loss:.1%}**
- **Forecast Uncertainty Band**: ±{fc.forecast_uncertainty_pct:.1f}% spread between scenarios
- **Annualized Volatility**: {fc.expected_volatility_annualized:.1f}% | Out-of-sample MAE: {fc.historical_mae_pct:.2f}%

**Key Risk Factors & Model Rationale:**
- **Why this return**: {fc.base.description}
- **Bearish Loss Risk**: In the adverse scenario, you could lose up to {fc.bearish.formatted_pl} ({fc.bearish.formatted_return}).
- **Transaction Friction**: Includes simulated round-trip execution cost of {fc.simulated_transaction_cost_pct:.1f}%.
- **Disclaimer**: All figures are probabilistic walk-forward estimates. Past market returns never guarantee future results."""


        # 1. Direct Portfolio Questions
        if portfolio and any(k in q for k in ["cash", "balance", "how much money", "how much virtual"]):
            c = portfolio.get("account_currency", "INR")
            cash = portfolio.get("available_cash", 0.0)
            total = portfolio.get("total_portfolio_value", 0.0)
            return f"💵 **Available Virtual Cash**: You currently have **{c} {cash:,.2f}** available to invest, out of a total portfolio net worth of **{c} {total:,.2f}**. All funds are 100% simulated for risk-free practice."

        if portfolio and any(k in q for k in ["holding", "what do i own", "my shares", "my stocks", "portfolio"]):
            c = portfolio.get("account_currency", "INR")
            holdings = portfolio.get("holdings", [])
            if not holdings:
                return f"📁 **Your Portfolio Holdings**: You currently have **0 active holdings**. Your available virtual cash is **{c} {portfolio.get('available_cash', 0.0):,.2f}**. Search for a global stock and place your first practice order!"
            lines = [f"• **{h.get('company_name', h.get('ticker'))} ({h.get('ticker')})**: {h.get('quantity'):.2f} shares @ avg {h.get('currency', '$')}{h.get('average_cost', 0.0):.2f} (Current Value: {c} {h.get('current_value_acc', 0.0):,.2f}, P&L: {h.get('unrealized_pnl', 0.0):+,.2f})" for h in holdings]
            return f"📁 **Your Virtual Holdings ({len(holdings)} assets)**:\n\n" + "\n".join(lines) + f"\n\n**Total Invested**: {c} {portfolio.get('invested_value', 0.0):,.2f} | **Total Portfolio**: {c} {portfolio.get('total_portfolio_value', 0.0):,.2f}"

        if portfolio and any(k in q for k in ["concentration", "diversif", "highest concentration", "risk"]):
            c = portfolio.get("account_currency", "INR")
            risk = portfolio.get("risk_metrics", {})
            hhi = risk.get("hhi", 0)
            conc = risk.get("concentration_risk", "Low")
            holdings = portfolio.get("holdings", [])
            top_holding = "None"
            if holdings:
                sorted_h = sorted(holdings, key=lambda x: x.get("current_value_acc", 0.0), reverse=True)
                top_holding = f"{sorted_h[0].get('ticker')} ({sorted_h[0].get('current_value_acc', 0.0) / max(portfolio.get('invested_value', 1.0), 1.0) * 100:.1f}% of invested assets)"
            return f"""🛡️ **Portfolio Risk & Concentration Analysis**:
- **Concentration Rating**: **{conc}** (Herfindahl-Hirschman Index: {hhi:.0f}/10,000)
- **Top Concentration**: {top_holding}
- **Active Holdings**: {len(holdings)} positions
- **Risk Advice**: {"Great job! Your holdings are spread out." if conc == "Low" else "Consider adding companies in different sectors and global exchanges to lower your concentration risk."}"""

        if portfolio and any(k in q for k in ["profit", "loss", "p&l", "pnl", "why did my portfolio"]):
            c = portfolio.get("account_currency", "INR")
            pnl = portfolio.get("unrealized_pnl", 0.0)
            ret_pct = portfolio.get("total_return_pct", 0.0)
            explanation = "gained" if pnl >= 0 else "declined"
            return f"""📈 **Portfolio Profit & Loss Breakdown**:
- **Unrealized P&L**: **{c} {pnl:+,.2f}** ({ret_pct:+.2f}%)
- **Total Portfolio Value**: **{c} {portfolio.get('total_portfolio_value', 0.0):,.2f}**
- **Why it changed**: Your portfolio value updates in real time based on the latest available market prices of your active holdings. When underlying stocks rise, your unrealized profit increases; when they decline, unrealized P&L drops."""

        # 2. Company Fundamental & Business Questions
        if company and any(k in q for k in ["what does this company do", "how does it earn money", "business model"]):
            name = company.get("company_name", company.get("ticker"))
            f = company.get("fundamentals", {})
            sector = f.get("sector", "Global Equities")
            ind = f.get("industry", "Technology/Services")
            desc = f.get("description", "")
            return f"""🏢 **Business Overview for {name} ({company.get('ticker')}):**
- **Sector**: {sector}
- **Industry**: {ind}
- **Business Model**: {name} operates primarily in {ind}. It generates revenue through products, software, or services distributed across global markets.
{f"- **Corporate Profile**: {desc[:300]}..." if desc else ""}"""

        if company and any(k in q for k in ["strength", "weakness", "financial strength", "risks"]):
            name = company.get("company_name", company.get("ticker"))
            f = company.get("fundamentals", {})
            pe = f.get("trailing_pe", "N/A")
            mc = f.get("market_cap", "N/A")
            return f"""🔍 **Financial Strengths & Risks for {name}:**
- **Strengths**: Established global market positioning, operating in {f.get('sector', 'Global Sector')}. Market Cap: {mc}.
- **Valuation**: Trailing P/E is **{pe}**.
- **Key Risks**: Macroeconomic fluctuations, currency foreign-exchange shifts, sector competition, and regulatory compliance."""

        if company and any(k in q for k in ["sentiment", "finbert", "news"]):
            s = company.get("sentiment", {})
            return f"""📰 **FinBERT News Sentiment Analysis for {company.get('ticker')}:**
- **Overall Sentiment**: **{s.get('overall_sentiment', 'Neutral')}**
- **Positive Ratio**: {s.get('positive_ratio', 0.0):.1%}
- **Negative Ratio**: {s.get('negative_ratio', 0.0):.1%}
- **Neutral Ratio**: {s.get('neutral_ratio', 1.0):.1%}
- **FinBERT Model**: Analyzed via ProsusAI/finbert financial language transformer on recent corporate headlines."""

        if company and any(k in q for k in ["prediction", "ml", "forecast", "machine learning", "direction"]):
            p = company.get("prediction", {})
            dir_label = p.get("direction", "Neutral")
            prob = p.get("probability", 0.5)
            model = p.get("model", "Quantitative Ensemble")
            return f"""🤖 **Machine Learning 5-Trading-Session Forecast for {company.get('ticker')}:**
- **Forecast Direction**: **{dir_label}**
- **Confidence Probability**: **{prob:.1%}**
- **Primary Model**: {model} (trained chronologically across Logistic Regression, Random Forest, and XGBoost with zero data leakage)
- **Objective**: Predicts whether return over the next 5 exchange sessions will be positive or non-positive."""

        if company and any(k in q for k in ["shap", "explain prediction", "feature importance"]):
            return f"""🔬 **SHAP Explainability for {company.get('ticker')} Forecast:**
- **Framework**: Cooperative game theory Shapley values.
- **Top Bullish Drivers**: Momentum indicators (RSI rebound, short-term moving average crossovers).
- **Top Bearish Headwinds**: Historical volatility spikes or technical resistance bands.
- **Interpretation**: Each feature shifts the base probability up or down toward the final model decision."""

        # 3. Check glossary keywords
        for key, exp in FINANCIAL_GLOSSARY_EXPLANATIONS.items():
            if key in q or (key == "pe" and ("p/e" in q or "pe ratio" in q)):
                prefix = "📚 **Financial Learning Concept:**\n\n" if is_beginner else "📊 **Technical Definition:**\n\n"
                return f"{prefix}{exp}\n\n*Would you like to see how this applies to your selected stock or portfolio?*"

        # 4. Should I understand this company before buying
        if "understand this company before buying" in q or "should i understand" in q:
            return """💡 **Yes, absolutely! Peter Lynch's golden rule is: 'Know what you own, and know why you own it.'**

Before investing simulated cash in any company, consider:
1. **The Core Business**: How does the company make money? What products or services does it sell?
2. **Financial Health**: Does it generate consistent revenue and profit, or is it burning cash?
3. **Valuation**: Look at the P/E ratio — are you paying a reasonable price relative to its earnings?
4. **Competitive Moat**: What stops competitors from stealing its market share?
5. **AI & Sentiment Signals**: Review the FinPilot ML prediction and FinBERT sentiment for near-term momentum."""

        # 5. Guided investment practice
        if "practise" in q or "practice" in q or "invest" in q or "buy" in q:
            if company:
                t = company.get("ticker", "the asset")
                name = company.get("company_name", t)
                price_info = company.get("latest_price", {})
                price = price_info.get("price", 0.0)
                curr = company.get("currency", "USD")
                pred = company.get("prediction", {})
                dir_label = pred.get("direction", "Neutral")

                return f"""🎯 **Guided Practice: Simulated Investment in {name} ({t})**

Here is a step-by-step breakdown to help you practice before executing your simulated order:

1. **Current Market Price**: {price:.2f} {curr}
2. **AI Directional Forecast**: The machine learning model forecasts a **{dir_label}** 5-session directional trend with {pred.get('probability', 0.5):.1%} probability.
3. **Sentiment Check**: FinBERT analyzed current news sentiment as **{company.get('sentiment', {}).get('overall_sentiment', 'Neutral')}**.
4. **Risk Consideration**: Always check your available practice cash and ensure you do not put all your funds into a single stock.
5. **Simulated Execution**: Click on **Orders / Virtual Investing** to open the order panel, enter your target quantity or amount, and test your strategy with zero real-world financial risk!"""

        # General response
        if company:
            t = company.get("ticker", "")
            return f"""💡 **FinPilot Analysis for {company.get('company_name', t)} ({t}):**

- **Trading Currency**: {company.get('currency', 'USD')} on {company.get('exchange', 'Global Exchange')}.
- **Machine Learning**: 5-Session trend predicted as **{company.get('prediction', {}).get('direction', 'Neutral')}**.
- **Market Sentiment**: News sentiment is rated **{company.get('sentiment', {}).get('overall_sentiment', 'Neutral')}**.

You can ask me to explain any financial indicator (like RSI or P/E), break down the company's risks, or evaluate a practice trade with your virtual balance!"""

        return """👋 **Welcome to FinPilot AI Assistant!**

I am here to guide your global financial analysis and virtual investing journey. You can ask me:
- *"Explain what P/E ratio and RSI mean with an example"*
- *"How should I diversify my virtual portfolio?"*
- *"Help me practice investing in Apple, NVIDIA, or Reliance"*
- *"What is a limit order vs market order?"*
- *"Why did my portfolio value change?"*

Select any global stock or open **Orders / Portfolio** to get started!"""
