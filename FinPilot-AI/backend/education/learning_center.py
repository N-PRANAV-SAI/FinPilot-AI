"""Beginner Financial Education & Interactive Learning Center for FinPilot AI.
Provides structured lessons, interactive quizzes, progress tracking, and glossary.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from database.models import LearningProgress

LESSONS_DATABASE = [
    {
        "id": "lesson_1",
        "title": "What is the Stock Market?",
        "category": "Foundations",
        "read_time": "3 min",
        "summary": "Understand how global marketplaces connect companies looking for growth capital with everyday investors.",
        "content": """The **stock market** is essentially a global network of regulated public marketplaces where people can buy and sell ownership pieces (shares) of corporations.

Imagine a giant digital farmer's market. Instead of apples and oranges, companies like Apple, NVIDIA, and Reliance bring tiny fractions of their ownership to trade with participants.

### Why do companies issue stock?
When companies want to invent new technologies, build factories, or expand internationally, they need capital. By issuing shares through an Initial Public Offering (IPO), they raise money from public investors rather than borrowing from banks.

### Key Takeaway:
The stock market allows anyone to own a fractional piece of the world's most productive and innovative enterprises.""",
        "quiz": {
            "question": "What is the primary reason companies sell stock to the public?",
            "options": [
                "To pay off their customers' debts",
                "To raise capital for business growth and expansion",
                "To reduce their product prices",
                "To avoid paying taxes"
            ],
            "correct_index": 1,
            "explanation": "Companies sell shares in order to raise equity capital to invest in research, hiring, infrastructure, and growth."
        }
    },
    {
        "id": "lesson_2",
        "title": "What is a Stock and a Share?",
        "category": "Foundations",
        "read_time": "3 min",
        "summary": "Learn what it means to be a fractional shareholder in a public corporation.",
        "content": """A **stock** represents legal fractional ownership in a business. A single unit of stock is called a **share**.

If a company is sliced into 1,000,000 equal slices and you purchase 100 shares, you legally own 0.01% of that business, including rights to its future profits and assets.

### As a shareholder, you can benefit in two main ways:
1. **Capital Appreciation**: The market price of the stock rises over time as the company grows more valuable.
2. **Dividends**: The company chooses to distribute a portion of its cash profits directly back to shareholders.""",
        "quiz": {
            "question": "If you own shares in a company, what are you legally entitled to?",
            "options": [
                "Free products from all their stores forever",
                "Fractional ownership in the company and rights to potential profits",
                "Guaranteed monthly payments regardless of performance",
                "The ability to fire company employees"
            ],
            "correct_index": 1,
            "explanation": "Shares represent fractional equity ownership in the firm, giving you a stake in its enterprise value and dividend distributions."
        }
    },
    {
        "id": "lesson_3",
        "title": "What is a Stock Exchange and Ticker?",
        "category": "Trading Mechanics",
        "read_time": "4 min",
        "summary": "How NASDAQ, NYSE, NSE, LSE, and TSE organize global trading and ticker symbols.",
        "content": """A **Stock Exchange** is the secure, audited venue where buyers and sellers meet to execute trades.

- **United States**: NYSE (New York Stock Exchange), NASDAQ
- **India**: NSE (National Stock Exchange), BSE (Bombay Stock Exchange)
- **Japan**: TSE (Tokyo Stock Exchange)
- **Germany**: XETRA / Frankfurt Stock Exchange
- **United Kingdom**: LSE (London Stock Exchange)

### What is a Ticker Symbol?
A **ticker symbol** is a short unique abbreviation used to identify a publicly traded company on an exchange:
- `NVDA` = NVIDIA Corporation on NASDAQ
- `RELIANCE.NS` = Reliance Industries on NSE India
- `7203.T` = Toyota Motor Corporation on Tokyo Stock Exchange
- `SIE.DE` = Siemens AG on XETRA Germany

Because multiple countries can have companies with similar names, tickers and exchange codes ensure exact clarity.""",
        "quiz": {
            "question": "Why is an exchange suffix (like .NS or .T) important in global investing?",
            "options": [
                "It determines how fast your internet connection is",
                "It identifies which global exchange and country the asset trades on",
                "It specifies the CEO's home country",
                "It changes the tax rate to zero"
            ],
            "correct_index": 1,
            "explanation": "Global tickers use exchange suffixes (e.g., .NS for National Stock Exchange of India, .T for Tokyo) to prevent confusion across international markets."
        }
    },
    {
        "id": "lesson_4",
        "title": "Market Orders vs Limit Orders",
        "category": "Trading Mechanics",
        "read_time": "4 min",
        "summary": "Master the difference between immediate execution and price-controlled orders.",
        "content": """When placing a trade, you have two primary choices for how your order is executed:

### 1. Market Order
A Market Order prioritizes **speed of execution** over price.
- You tell the exchange: *"Buy/sell right now at whatever price is currently available."*
- Useful when you want immediate entry or exit.

### 2. Limit Order
A Limit Order prioritizes **price certainty** over speed.
- You specify the maximum price you are willing to pay (Buy Limit) or minimum price you will accept (Sell Limit).
- If the stock never reaches your limit price, the order remains **Pending** and never executes.

### Beginner Rule of Thumb:
Use Limit Orders whenever trading during volatile market openings or with assets that have wide bid-ask spreads.""",
        "quiz": {
            "question": "What is the key advantage of a Limit Order?",
            "options": [
                "It guarantees that the order will execute within 5 seconds",
                "It prevents buying higher or selling lower than your specified price target",
                "It eliminates all investment risk",
                "It doubles your profit automatically"
            ],
            "correct_index": 1,
            "explanation": "A Limit order guarantees price boundary control — you will only execute at your target price or better."
        }
    },
    {
        "id": "lesson_5",
        "title": "What is Market Capitalization?",
        "category": "Financial Valuation",
        "read_time": "3 min",
        "summary": "Large-Cap vs Mid-Cap vs Small-Cap and how company size affects stability and risk.",
        "content": """**Market Capitalization** (or 'Market Cap') is the total aggregate market value of all of a company's outstanding shares.

Formula:
$$\\text{Market Cap} = \\text{Share Price} \\times \\text{Total Outstanding Shares}$$

### Market Cap Categories:
1. **Mega-Cap / Large-Cap** ($10B+ / ₹80,000 Cr+):
   - Examples: Microsoft, Apple, Reliance Industries, TCS.
   - Characteristics: Mature, established businesses, strong cash flows, generally lower volatility.
2. **Mid-Cap** ($2B - $10B):
   - Fast-growing companies with proven products, but higher volatility.
3. **Small-Cap** (Under $2B):
   - Younger or niche companies. High growth potential, but significantly higher risk of failure.""",
        "quiz": {
            "question": "If a company has 10 million shares priced at $50 each, what is its Market Cap?",
            "options": [
                "$50 million",
                "$500 million",
                "$5 billion",
                "$100 million"
            ],
            "correct_index": 1,
            "explanation": "10,000,000 shares × $50 = $500,000,000 ($500M)."
        }
    },
    {
        "id": "lesson_6",
        "title": "P/E Ratio and EPS Explained Simply",
        "category": "Financial Valuation",
        "read_time": "4 min",
        "summary": "How to tell whether a stock is priced expensively or reasonably compared to its actual earnings.",
        "content": """### EPS (Earnings Per Share)
EPS is the net profit a company generates for each individual share of its stock.
$$\\text{EPS} = \\frac{\\text{Net Income}}{\\text{Total Outstanding Shares}}$$

### P/E Ratio (Price-to-Earnings)
The P/E ratio reveals how many dollars/rupees investors are currently willing to pay for each single dollar/rupee of current earnings.
$$\\text{P/E} = \\frac{\\text{Stock Price}}{\\text{Earnings Per Share (EPS)}}$$

### How to interpret P/E:
- **Low P/E (e.g. 10 - 15)**: May indicate a mature, slow-growth value company, or that the market expects future earnings to decline.
- **High P/E (e.g. 35 - 70+)**: Indicates the market expects explosive revenue and profit growth in future years (common in AI and tech).
- **Negative P/E**: The company is currently operating at a net loss.""",
        "quiz": {
            "question": "What does a P/E ratio of 25 mean?",
            "options": [
                "The stock price will increase by 25% this year",
                "Investors are paying $25 for every $1 of the company's annual earnings",
                "The company has 25 competitors in its industry",
                "The company has been public for 25 years"
            ],
            "correct_index": 1,
            "explanation": "P/E represents the price multiple: investors are paying 25 currency units per unit of annual net profit."
        }
    },
    {
        "id": "lesson_7",
        "title": "Technical Indicators: RSI and MACD",
        "category": "Technical Analysis",
        "read_time": "5 min",
        "summary": "Learn how momentum indicators help quantify short-term market psychology.",
        "content": """While fundamental analysis inspects the business financials, **Technical Analysis** evaluates market price action and momentum.

### 1. Relative Strength Index (RSI)
- RSI ranges from 0 to 100 based on recent gains versus recent losses over 14 trading periods.
- **Above 70 (Overbought)**: Price has surged rapidly; buying momentum may be stretched.
- **Below 30 (Oversold)**: Price has fallen sharply; selling pressure may be exhausted.

### 2. MACD (Moving Average Convergence Divergence)
- Compares the 12-day exponential moving average (EMA) with the 26-day EMA.
- When the MACD line crosses **above** the 9-day Signal line, it signals emerging bullish momentum.
- When it crosses **below**, it signals emerging bearish momentum.""",
        "quiz": {
            "question": "An RSI reading of 22 typically indicates which market condition?",
            "options": [
                "The asset is heavily overbought and guaranteed to rise",
                "The asset is technically oversold after heavy recent selling pressure",
                "The stock exchange is closed for holidays",
                "The company has doubled its profit"
            ],
            "correct_index": 1,
            "explanation": "RSI readings below 30 are considered oversold, meaning recent downward price momentum has been exceptionally severe."
        }
    },
    {
        "id": "lesson_8",
        "title": "Diversification and Risk Management",
        "category": "Portfolio Strategy",
        "read_time": "4 min",
        "summary": "Why putting all your virtual eggs in one basket is the #1 mistake new investors make.",
        "content": """### The Golden Rule of Investing:
*"Do not put all your eggs in one basket."*

### What is Concentration Risk?
If you have ₹1,00,000 in your account and invest ₹90,000 into a single high-flying tech stock, a bad earnings report or regulatory fine can wipe out 30% of your entire net worth in a single day.

### How to Diversify:
1. **Across Sectors**: Combine Technology, Healthcare, Consumer Goods, and Financials.
2. **Across Geographies**: Hold companies in the US, India, Europe, and Asia.
3. **Cash Buffer**: Keep 10%–20% in available cash to take advantage of market dips.

By holding 8 to 15 quality companies across diverse sectors, a bad quarter for one company is cushioned by steady performance from others.""",
        "quiz": {
            "question": "What is the primary benefit of portfolio diversification?",
            "options": [
                "It guarantees that you will never experience a losing trade",
                "It reduces overall portfolio volatility and protects against catastrophic single-stock losses",
                "It doubles the dividend yield of every stock automatically",
                "It eliminates the need to do research"
            ],
            "correct_index": 1,
            "explanation": "Diversification reduces unsystematic risk — ensuring that adversity in one company or sector does not sink your overall wealth."
        }
    },
    {
        "id": "lesson_9",
        "title": "What is Paper Trading and Why Does It Matter?",
        "category": "Practical Skills",
        "read_time": "3 min",
        "summary": "How simulated investing builds discipline, strategy, and risk awareness before using real money.",
        "content": """**Paper Trading** (also called virtual or simulated investing) allows you to practice buying and selling real global stocks using **fake money** while tracking real market quotes.

### Why Paper Trading is Crucial:
1. **Zero Financial Risk**: Learn from your mistakes without losing real-world savings.
2. **Emotional Calibration**: Experience how market fluctuations feel without panic.
3. **Test AI Models & Strategies**: See how FinPilot AI's machine learning predictions and FinBERT sentiment perform over actual trading horizons.
4. **Order Familiarity**: Master limit orders, stop conditions, and currency conversions.

### FinPilot Safety Rule:
All transactions in FinPilot AI are 100% simulated paper trades. Treat your virtual capital with the same respect as real money to build good lifelong habits!""",
        "quiz": {
            "question": "What is the best way to use paper trading effectively?",
            "options": [
                "Make random million-dollar bets because it's not real money",
                "Treat your virtual balance with the same disciplined strategy and risk management as real funds",
                "Ignore company fundamentals completely",
                "Never sell any holding under any circumstances"
            ],
            "correct_index": 1,
            "explanation": "Treating virtual capital seriously builds the emotional discipline and risk habits required for lifelong investing success."
        }
    }
]


class LearningCenterService:
    """Manages lesson curriculum, quiz evaluations, and user progress."""

    @staticmethod
    def get_all_lessons(user_id: int, db: Session) -> List[Dict[str, Any]]:
        """Return all lessons annotated with the user's completion status."""
        progress_records = db.query(LearningProgress).filter(LearningProgress.user_id == user_id).all()
        progress_map = {p.lesson_id: p for p in progress_records}

        lessons_with_status = []
        for l in LESSONS_DATABASE:
            rec = progress_map.get(l["id"])
            lessons_with_status.append({
                **l,
                "completed": rec.completion_status if rec else False,
                "quiz_score": rec.quiz_score if rec else 0.0
            })
        return lessons_with_status

    @staticmethod
    def get_lesson_by_id(lesson_id: str) -> Optional[Dict[str, Any]]:
        """Fetch a specific lesson."""
        for l in LESSONS_DATABASE:
            if l["id"] == lesson_id:
                return l
        return None

    @staticmethod
    def submit_quiz_answer(user_id: int, lesson_id: str, selected_option_index: int, db: Session) -> Dict[str, Any]:
        """Validate quiz response, record score, and update user learning progress."""
        lesson = LearningCenterService.get_lesson_by_id(lesson_id)
        if not lesson or "quiz" not in lesson:
            return {"success": False, "error": "Lesson or quiz not found."}

        quiz = lesson["quiz"]
        is_correct = (selected_option_index == quiz["correct_index"])
        score = 100.0 if is_correct else 0.0

        rec = db.query(LearningProgress).filter(
            LearningProgress.user_id == user_id,
            LearningProgress.lesson_id == lesson_id
        ).first()

        if not rec:
            rec = LearningProgress(
                user_id=user_id,
                lesson_id=lesson_id,
                completion_status=is_correct,
                quiz_score=score,
                updated_at=datetime.now(timezone.utc)
            )
            db.add(rec)
        else:
            rec.completion_status = is_correct or rec.completion_status
            rec.quiz_score = max(rec.quiz_score, score)
            rec.updated_at = datetime.now(timezone.utc)

        db.commit()

        return {
            "success": True,
            "is_correct": is_correct,
            "score": score,
            "explanation": quiz["explanation"],
            "correct_index": quiz["correct_index"]
        }
