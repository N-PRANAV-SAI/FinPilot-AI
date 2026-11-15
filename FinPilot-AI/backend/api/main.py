"""FastAPI REST API Server for FinPilot AI.
Provides complete institutional-grade REST endpoints for Auth, Onboarding,
Paper Trading, Portfolio Management, AI Assistant, and Financial Education.
"""
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Union
from sqlalchemy.orm import Session

from database.db import get_session, init_db
from database.models import User, VirtualOrders, VirtualTransactions, Watchlist
from backend.services.auth_service import (
    register_user, authenticate_user, save_onboarding_preferences, decode_access_token
)
from backend.trading.paper_engine import PaperTradingEngine
from backend.assistant.ai_assistant import FinPilotAIAssistant
from backend.education.learning_center import LearningCenterService
from backend.data.company_search import search_companies
from backend.data.market_data import get_latest_price
from backend.data.global_exchanges import GLOBAL_EXCHANGES

app = FastAPI(
    title="FinPilot AI REST API",
    description="Enterprise Global Financial Analysis, Virtual Paper Trading, and AI Mentorship Platform",
    version="2.0.0"
)

# Enable CORS for React / Vite / Next.js / Streamlit frontends
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

assistant = FinPilotAIAssistant()

# Initialize DB tables on startup
@app.on_event("startup")
def on_startup():
    init_db()


# -------------------------------------------------------------
# Pydantic Request / Response Schemas
# -------------------------------------------------------------
class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str

class OnboardingRequest(BaseModel):
    user_id: int
    experience_level: str
    learning_goals: List[str]
    risk_comfort: str
    preferred_currency: str
    practice_balance: float
    trading_mode: str

class BuyOrderRequest(BaseModel):
    user_id: int
    ticker: str
    company_name: str
    exchange: str
    country: str
    currency: str
    order_type: str = "MARKET"
    quantity: Optional[float] = None
    investment_amount_acc: Optional[float] = None
    limit_price: Optional[float] = None

class SellOrderRequest(BaseModel):
    user_id: int
    ticker: str
    quantity: float

class ResetAccountRequest(BaseModel):
    user_id: int
    new_balance: Optional[float] = None

class AddFundsRequest(BaseModel):
    user_id: int
    amount: float

class AssistantChatRequest(BaseModel):
    user_id: int
    message: str
    ticker: Optional[str] = None
    portfolio_context: Optional[Dict[str, Any]] = None

class QuizSubmitRequest(BaseModel):
    user_id: int
    lesson_id: str
    selected_option_index: int

class WatchlistAddRequest(BaseModel):
    user_id: int
    ticker: str
    company_name: Optional[str] = None
    exchange: Optional[str] = None
    country: Optional[str] = None
    currency: Optional[str] = None

class WatchlistRemoveRequest(BaseModel):
    user_id: int
    ticker: str

class ForecastPredictRequest(BaseModel):
    ticker: str
    investment_amount: float = Field(..., gt=0)
    duration: Union[str, int] = "1m"
    target_amount: Optional[float] = None
    risk_level: str = "Moderate"
    account_currency: str = "INR"

class GoalSimulateRequest(BaseModel):
    starting_capital: float = Field(..., gt=0)
    target_amount: float = Field(..., gt=0)
    time_available: Union[str, int] = "1 month"
    currency: str = "INR"
    ticker: Optional[str] = None

class PortfolioSimulateRequest(BaseModel):
    allocations: List[Dict[str, Any]]
    total_capital: Optional[float] = None
    duration: Union[str, int] = "1m"
    account_currency: str = "INR"
    risk_level: str = "Moderate"


# -------------------------------------------------------------
# Endpoints: System & Health
# -------------------------------------------------------------
@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "service": "FinPilot AI Enterprise API",
        "version": "2.0.0",
        "paper_trading": "ACTIVE (100% Virtual Money)"
    }

@app.get("/api/exchanges")
def get_exchanges():
    return {"exchanges": GLOBAL_EXCHANGES}


# -------------------------------------------------------------
# Endpoints: Authentication & User Onboarding
# -------------------------------------------------------------
@app.post("/api/auth/register")
def register(req: RegisterRequest, db: Session = Depends(get_session)):
    res = register_user(req.name, req.email, req.password, db)
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error"))
    return res

@app.post("/api/auth/login")
def login(req: LoginRequest, db: Session = Depends(get_session)):
    res = authenticate_user(req.email, req.password, db)
    if not res.get("success"):
        raise HTTPException(status_code=401, detail=res.get("error"))
    return res

@app.post("/api/auth/onboarding")
def save_onboarding(req: OnboardingRequest, db: Session = Depends(get_session)):
    res = save_onboarding_preferences(
        user_id=req.user_id,
        experience_level=req.experience_level,
        learning_goals=req.learning_goals,
        risk_comfort=req.risk_comfort,
        preferred_currency=req.preferred_currency,
        practice_balance=req.practice_balance,
        trading_mode=req.trading_mode,
        db=db
    )
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error"))
    return res

@app.get("/api/auth/user/{user_id}")
def get_user(user_id: int, db: Session = Depends(get_session)):
    u = db.query(User).filter(User.user_id == user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "user_id": u.user_id,
        "name": u.name,
        "email": u.email,
        "experience_level": u.experience_level,
        "learning_goals": u.learning_goals,
        "risk_comfort": u.risk_comfort,
        "preferred_currency": u.preferred_currency,
        "preferred_mode": u.preferred_mode,
        "onboarding_completed": u.onboarding_completed,
        "created_at": u.created_at.isoformat() if u.created_at else None
    }


# -------------------------------------------------------------
# Endpoints: Paper Trading & Virtual Portfolio
# -------------------------------------------------------------
@app.get("/api/portfolio/{user_id}")
def get_portfolio(user_id: int, db: Session = Depends(get_session)):
    return PaperTradingEngine.get_user_account_summary(user_id, db)

@app.post("/api/trading/buy")
def execute_buy(req: BuyOrderRequest, db: Session = Depends(get_session)):
    res = PaperTradingEngine.execute_buy_order(
        user_id=req.user_id,
        ticker=req.ticker,
        company_name=req.company_name,
        exchange=req.exchange,
        country=req.country,
        currency=req.currency,
        order_type=req.order_type,
        quantity=req.quantity,
        investment_amount_acc=req.investment_amount_acc,
        limit_price=req.limit_price,
        db=db
    )
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error"))
    return res

@app.post("/api/trading/sell")
def execute_sell(req: SellOrderRequest, db: Session = Depends(get_session)):
    res = PaperTradingEngine.execute_sell_order(
        user_id=req.user_id,
        ticker=req.ticker,
        quantity=req.quantity,
        db=db
    )
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error"))
    return res

@app.post("/api/trading/reset")
def reset_account(req: ResetAccountRequest, db: Session = Depends(get_session)):
    return PaperTradingEngine.reset_virtual_account(req.user_id, req.new_balance, db)

@app.post("/api/trading/deposit")
def add_funds(req: AddFundsRequest, db: Session = Depends(get_session)):
    return PaperTradingEngine.add_virtual_funds(req.user_id, req.amount, db)

@app.get("/api/trading/orders/{user_id}")
def get_orders(user_id: int, db: Session = Depends(get_session)):
    orders = db.query(VirtualOrders).filter(VirtualOrders.user_id == user_id).order_by(VirtualOrders.created_at.desc()).all()
    return [
        {
            "order_id": o.order_id,
            "ticker": o.ticker,
            "company_name": o.company_name,
            "exchange": o.exchange,
            "order_type": o.order_type,
            "side": o.side,
            "quantity": o.quantity,
            "execution_price": o.execution_price,
            "order_status": o.order_status,
            "created_at": o.created_at.isoformat() if o.created_at else None
        }
        for o in orders
    ]

@app.get("/api/trading/transactions/{user_id}")
def get_transactions(user_id: int, db: Session = Depends(get_session)):
    txs = db.query(VirtualTransactions).filter(VirtualTransactions.user_id == user_id).order_by(VirtualTransactions.transaction_date.desc()).all()
    return [
        {
            "transaction_id": t.transaction_id,
            "ticker": t.ticker,
            "company_name": t.company_name,
            "type": t.transaction_type,
            "quantity": t.quantity,
            "price": t.price,
            "total_amount": t.total_amount,
            "currency": t.currency,
            "realized_pnl": t.realized_pnl,
            "date": t.transaction_date.isoformat() if t.transaction_date else None
        }
        for t in txs
    ]


# -------------------------------------------------------------
# Endpoints: Market Search & Analysis
# -------------------------------------------------------------
@app.get("/api/market/search")
def search(query: str, country: Optional[str] = None):
    return {"results": search_companies(query, country_filter=country)}

@app.get("/api/market/quote/{ticker}")
def get_quote(ticker: str):
    res = get_latest_price(ticker)
    if not res:
        raise HTTPException(status_code=404, detail="Quote not found")
    return res

@app.get("/api/market/analysis/{ticker}")
def analyze(ticker: str):
    """Run full ML + FinBERT + SHAP + RAG + LLM analysis pipeline. Returns JSON-safe result."""
    try:
        from backend.services.analysis_service import run_full_analysis
        import pandas as pd
        import numpy as np

        raw = run_full_analysis(ticker)

        # Serialize DataFrames and numpy types to JSON-safe dicts
        def _safe(obj):
            if isinstance(obj, pd.DataFrame):
                return obj.head(500).reset_index().to_dict(orient="records")
            if isinstance(obj, pd.Series):
                return obj.to_dict()
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            if isinstance(obj, (np.integer,)):
                return int(obj)
            if isinstance(obj, (np.floating,)):
                return float(obj)
            return obj

        # Build the JSON-safe response with training results
        quant = raw.get("training", {})
        hybrid = raw.get("hybrid_training")
        shap_info = raw.get("shap_info")

        model_comparison = {}
        for name, r in quant.get("results", {}).items():
            model_comparison[name] = {
                "validation": r.get("validation", {}),
                "test": r.get("test", {}),
            }

        hybrid_comparison = None
        if hybrid:
            hybrid_comparison = {}
            for name, r in hybrid.get("results", {}).items():
                hybrid_comparison[name] = {
                    "validation": r.get("validation", {}),
                    "test": r.get("test", {}),
                }

        prediction = raw.get("prediction", {})
        sentiment = raw.get("sentiment", {})
        sentiment_articles = None
        if raw.get("sentiment_df") is not None and not raw["sentiment_df"].empty:
            sentiment_articles = raw["sentiment_df"].to_dict(orient="records")

        result = {
            "ticker": raw.get("ticker"),
            "company_name": raw.get("company_name"),
            "country": raw.get("country"),
            "exchange": raw.get("exchange"),
            "currency": raw.get("currency"),
            "currency_symbol": raw.get("currency_symbol"),
            "flag": raw.get("flag"),
            "latest_price": raw.get("latest_price"),
            "fundamentals": raw.get("fundamentals"),
            "last_market_date": raw.get("last_market_date"),
            # ML Prediction
            "prediction": prediction,
            # Model Comparison (Quant)
            "quant_models": {
                "selected_model": quant.get("selected_model"),
                "model_comparison": model_comparison,
                "features": quant.get("features", []),
                "train_size": quant.get("train_size"),
                "val_size": quant.get("val_size"),
                "test_size": quant.get("test_size"),
                "model_path": quant.get("model_path"),
                "is_hybrid": False,
            },
            # Hybrid Model Comparison
            "hybrid_models": {
                "selected_model": hybrid.get("selected_model") if hybrid else None,
                "model_comparison": hybrid_comparison,
                "features": hybrid.get("features", []) if hybrid else [],
                "train_size": hybrid.get("train_size") if hybrid else None,
                "val_size": hybrid.get("val_size") if hybrid else None,
                "test_size": hybrid.get("test_size") if hybrid else None,
                "is_hybrid": True,
            } if hybrid else None,
            # FinBERT Sentiment
            "sentiment": sentiment,
            "sentiment_articles": sentiment_articles,
            # SHAP
            "shap": shap_info,
            # News
            "news": raw.get("news"),
            # Filings
            "filings": raw.get("filings"),
            # LLM Explanation
            "llm_explanation": raw.get("llm_explanation"),
        }

        return result
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# -------------------------------------------------------------
# Endpoints: AI Financial Assistant
# -------------------------------------------------------------
@app.post("/api/assistant/chat")
def chat(req: AssistantChatRequest, db: Session = Depends(get_session)):
    u = db.query(User).filter(User.user_id == req.user_id).first()
    profile = {
        "name": u.name if u else "Investor",
        "experience_level": u.experience_level if u else "Beginner",
        "preferred_currency": u.preferred_currency if u else "INR"
    }

    port_ctx = PaperTradingEngine.get_user_account_summary(req.user_id, db)
    
    company_ctx = None
    if req.ticker:
        try:
            quote = get_latest_price(req.ticker)
            company_ctx = {
                "ticker": req.ticker,
                "latest_price": quote,
                "currency": quote.get("currency", "USD"),
            }
        except Exception:
            pass

    reply = assistant.generate_response(
        user_message=req.message,
        user_profile=profile,
        portfolio_context=port_ctx,
        company_context=company_ctx
    )
    return {"reply": reply}


# -------------------------------------------------------------
# Endpoints: AI Profit Forecasting & Investment Simulators
# -------------------------------------------------------------
@app.post("/api/forecast/predict")
def predict_forecast(req: ForecastPredictRequest):
    """Generate probabilistic return forecast and Bearish/Base/Bullish scenarios."""
    try:
        from backend.ml.return_forecasting import ReturnForecastingEngine
        engine = ReturnForecastingEngine()
        result = engine.predict_return_distribution(
            ticker=req.ticker,
            investment_amount=req.investment_amount,
            duration=req.duration,
            target_amount=req.target_amount,
            risk_level=req.risk_level,
            account_currency=req.account_currency,
        )
        return result.to_dict()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Return forecasting failed: {str(e)}")

@app.post("/api/forecast/goal")
def simulate_goal(req: GoalSimulateRequest):
    """Simulate compounding hurdles and statistical reality check for financial goals."""
    try:
        from backend.ml.goal_simulator import InvestmentGoalSimulator
        asset_vol = None
        asset_drift = None
        if req.ticker:
            from backend.data.market_data import fetch_market_data
            df = fetch_market_data(req.ticker, period="1y")
            if df is not None and len(df) > 20:
                ret = df["Close"].pct_change().dropna()
                asset_vol = float(ret.std() * (252 ** 0.5) * 100)
                asset_drift = float(ret.mean() * 252)

        result = InvestmentGoalSimulator.simulate_goal(
            starting_capital=req.starting_capital,
            target_amount=req.target_amount,
            time_available=req.time_available,
            currency=req.currency,
            asset_annual_volatility=asset_vol,
            asset_expected_drift=asset_drift,
        )
        return result.to_dict()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Goal simulation failed: {str(e)}")

@app.post("/api/forecast/portfolio")
def simulate_portfolio(req: PortfolioSimulateRequest):
    """Simulate multi-asset portfolio with historical covariance and correlation modeling."""
    try:
        from backend.ml.portfolio_simulator import MultiStockPortfolioSimulator
        simulator = MultiStockPortfolioSimulator()
        result = simulator.simulate_portfolio(
            allocations=req.allocations,
            total_capital=req.total_capital,
            duration=req.duration,
            account_currency=req.account_currency,
            risk_level=req.risk_level,
        )
        return result.to_dict()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Portfolio simulation failed: {str(e)}")



# -------------------------------------------------------------
# Endpoints: Watchlist Management
# -------------------------------------------------------------
@app.get("/api/watchlist/{user_id}")
def get_watchlist(user_id: int, db: Session = Depends(get_session)):
    items = db.query(Watchlist).filter(Watchlist.user_id == user_id).order_by(Watchlist.added_at.desc()).all()
    out = []
    for it in items:
        q = get_latest_price(it.ticker)
        out.append({
            "id": it.id,
            "ticker": it.ticker,
            "company_name": it.company_name or it.ticker,
            "exchange": it.exchange or "Global",
            "country": it.country or "",
            "currency": it.currency or q.get("currency", "USD"),
            "price": q.get("price", 0.0),
            "change": q.get("change", 0.0),
            "change_pct": q.get("change_pct", 0.0),
            "formatted_close": q.get("formatted_close", "N/A"),
            "formatted_change": q.get("formatted_change", "N/A"),
        })
    return {"watchlist": out}

@app.post("/api/watchlist/add")
def add_to_watchlist(req: WatchlistAddRequest, db: Session = Depends(get_session)):
    clean_ticker = req.ticker.strip().upper()
    existing = db.query(Watchlist).filter(Watchlist.user_id == req.user_id, Watchlist.ticker == clean_ticker).first()
    if existing:
        return {"success": True, "message": f"{clean_ticker} is already in your watchlist."}
    item = Watchlist(
        user_id=req.user_id,
        ticker=clean_ticker,
        company_name=req.company_name or clean_ticker,
        exchange=req.exchange or "",
        country=req.country or "",
        currency=req.currency or "USD",
    )
    db.add(item)
    db.commit()
    return {"success": True, "message": f"Added {clean_ticker} to watchlist."}

@app.post("/api/watchlist/remove")
def remove_from_watchlist(req: WatchlistRemoveRequest, db: Session = Depends(get_session)):
    clean_ticker = req.ticker.strip().upper()
    item = db.query(Watchlist).filter(Watchlist.user_id == req.user_id, Watchlist.ticker == clean_ticker).first()
    if item:
        db.delete(item)
        db.commit()
    return {"success": True, "message": f"Removed {clean_ticker} from watchlist."}


# -------------------------------------------------------------
# Endpoints: Market Overview, Indices & Technical Charting
# -------------------------------------------------------------
GLOBAL_INDICES = [
    {"name": "S&P 500", "ticker": "^GSPC", "country": "United States", "flag": "🇺🇸"},
    {"name": "NIFTY 50", "ticker": "^NSEI", "country": "India", "flag": "🇮🇳"},
    {"name": "DAX", "ticker": "^GDAXI", "country": "Germany", "flag": "🇩🇪"},
    {"name": "NIKKEI 225", "ticker": "^N225", "country": "Japan", "flag": "🇯🇵"},
]

@app.get("/api/market/indices")
def get_indices():
    out = []
    for idx in GLOBAL_INDICES:
        q = get_latest_price(idx["ticker"])
        out.append({
            "name": idx["name"],
            "ticker": idx["ticker"],
            "country": idx["country"],
            "flag": idx["flag"],
            "price": q.get("price", 0.0),
            "change": q.get("change", 0.0),
            "change_pct": q.get("change_pct", 0.0),
            "formatted_close": q.get("formatted_close", "N/A"),
            "formatted_change": q.get("formatted_change", "N/A"),
        })
    return {"indices": out}

@app.get("/api/market/company/{ticker}")
def get_company_details(ticker: str):
    """Fast non-blocking overview of company quote, fundamentals, news, and filings."""
    try:
        from backend.data.financial_data import fetch_fundamentals
        from backend.data.news_data import fetch_news
        from backend.data.filings_data import discover_company_documents

        clean_ticker = ticker.strip().upper()
        quote = get_latest_price(clean_ticker)
        fundamentals = fetch_fundamentals(clean_ticker)
        company_name = fundamentals.get("company_name", clean_ticker)
        country = fundamentals.get("country", "Global")
        exchange = fundamentals.get("exchange", "Global")
        news = fetch_news(clean_ticker, company_name=company_name, exchange=exchange)
        filings = discover_company_documents(clean_ticker, company_name=company_name, country=country, exchange=exchange, limit=6)

        return {
            "ticker": clean_ticker,
            "company_name": company_name,
            "quote": quote,
            "fundamentals": fundamentals,
            "news": news,
            "filings": filings,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/market/history/{ticker}")
def get_market_history(ticker: str, period: str = "1y", interval: str = "1d"):
    """Fetch candlestick OHLCV data with SMA20, SMA50, EMA20, RSI14, and MACD indicators."""
    try:
        import pandas as pd
        import numpy as np
        from backend.data.market_data import fetch_market_data

        clean_ticker = ticker.strip().upper()
        df = fetch_market_data(clean_ticker, period=period, interval=interval)
        close = df["Close"].astype(float)
        high = df["High"].astype(float)
        low = df["Low"].astype(float)
        volume = df["Volume"].astype(float)

        sma20 = close.rolling(20, min_periods=1).mean()
        sma50 = close.rolling(50, min_periods=1).mean()
        ema20 = close.ewm(span=20, adjust=False).mean()

        # RSI 14
        delta = close.diff()
        gain = delta.clip(lower=0).ewm(alpha=1/14, min_periods=1, adjust=False).mean()
        loss = (-delta.clip(upper=0)).ewm(alpha=1/14, min_periods=1, adjust=False).mean()
        rs = gain / loss.replace(0, 0.0001)
        rsi = 100 - (100 / (1 + rs))

        # MACD (12, 26, 9)
        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        macd_line = ema12 - ema26
        signal_line = macd_line.ewm(span=9, adjust=False).mean()
        macd_hist = macd_line - signal_line

        candles = []
        for i, dt in enumerate(df.index):
            d_str = str(dt.date()) if hasattr(dt, "date") else str(dt)[:10]
            s20 = sma20.iloc[i]
            s50 = sma50.iloc[i]
            e20 = ema20.iloc[i]
            r = rsi.iloc[i]
            m = macd_line.iloc[i]
            ms = signal_line.iloc[i]
            mh = macd_hist.iloc[i]
            candles.append({
                "date": d_str,
                "open": round(float(df["Open"].iloc[i]), 2),
                "high": round(float(high.iloc[i]), 2),
                "low": round(float(low.iloc[i]), 2),
                "close": round(float(close.iloc[i]), 2),
                "volume": round(float(volume.iloc[i]), 2),
                "sma20": round(float(s20), 2) if not pd.isna(s20) else None,
                "sma50": round(float(s50), 2) if not pd.isna(s50) else None,
                "ema20": round(float(e20), 2) if not pd.isna(e20) else None,
                "rsi": round(float(r), 2) if not pd.isna(r) else 50.0,
                "macd": round(float(m), 2) if not pd.isna(m) else 0.0,
                "macd_signal": round(float(ms), 2) if not pd.isna(ms) else 0.0,
                "macd_hist": round(float(mh), 2) if not pd.isna(mh) else 0.0,
            })

        return {"ticker": clean_ticker, "period": period, "candles": candles}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# -------------------------------------------------------------
# Endpoints: Beginner Learning Center
# -------------------------------------------------------------
@app.get("/api/education/lessons/{user_id}")
def get_lessons(user_id: int, db: Session = Depends(get_session)):
    return {"lessons": LearningCenterService.get_all_lessons(user_id, db)}

@app.post("/api/education/quiz")
def submit_quiz(req: QuizSubmitRequest, db: Session = Depends(get_session)):
    return LearningCenterService.submit_quiz_answer(
        user_id=req.user_id,
        lesson_id=req.lesson_id,
        selected_option_index=req.selected_option_index,
        db=db
    )


# -------------------------------------------------------------
# Endpoints: RAG — Document Upload & Evidence Retrieval
# -------------------------------------------------------------
from fastapi import File, UploadFile

@app.post("/api/rag/upload")
async def rag_upload_document(
    ticker: str,
    file: UploadFile = File(...),
    document_title: Optional[str] = None,
    filing_date: Optional[str] = None,
):
    """Upload a PDF financial report and ingest it into the RAG vector store."""
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")
    if file.size and file.size > 50 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File size exceeds 50 MB limit.")

    try:
        from backend.rag.retriever import FinancialRetriever
        from backend.rag.document_loader import load_pdf
        from io import BytesIO

        content = await file.read()
        pdf_bytes = BytesIO(content)
        clean_ticker = ticker.strip().upper()

        metadata = {
            "ticker": clean_ticker,
            "document_title": document_title or file.filename,
            "filing_date": filing_date or "",
            "original_filename": file.filename,
        }

        pages = load_pdf(pdf_bytes, metadata)
        if not pages:
            raise HTTPException(status_code=422, detail="No readable text found in the uploaded PDF.")

        retriever = FinancialRetriever()
        chunk_count = retriever.ingest(pages, clean_ticker, metadata)

        return {
            "success": True,
            "ticker": clean_ticker,
            "document_title": metadata["document_title"],
            "pages_extracted": len(pages),
            "chunks_indexed": chunk_count,
            "message": f"Successfully ingested {chunk_count} chunks from '{file.filename}' for {clean_ticker}.",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Document ingestion failed: {e}")


@app.get("/api/rag/query")
def rag_query(ticker: str, question: str, k: int = 5):
    """Query the RAG vector store for evidence passages relevant to a company."""
    try:
        from backend.rag.retriever import FinancialRetriever

        clean_ticker = ticker.strip().upper()
        retriever = FinancialRetriever()
        results = retriever.retrieve(question=question, ticker=clean_ticker, k=k)

        return {
            "ticker": clean_ticker,
            "question": question,
            "evidence": results,
            "count": len(results),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"RAG query failed: {e}")


@app.get("/api/rag/stats")
def rag_stats():
    """Return RAG vector store statistics."""
    try:
        from backend.rag.retriever import FinancialRetriever
        retriever = FinancialRetriever()
        return retriever.get_stats()
    except Exception as e:
        return {"total_chunks": 0, "error": str(e)}


# -------------------------------------------------------------
# Single Page Application (SPA) Static Files Serving
# -------------------------------------------------------------
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from pathlib import Path

FRONTEND_DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if not FRONTEND_DIST.exists():
    FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"

if (FRONTEND_DIST / "assets").exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets")), name="assets")

@app.get("/", response_class=HTMLResponse)
@app.get("/{full_path:path}", response_class=HTMLResponse)
def serve_spa(full_path: str = ""):
    if full_path.startswith("api/") or full_path.startswith("docs") or full_path.startswith("openapi.json") or full_path.startswith("redoc"):
        raise HTTPException(status_code=404, detail="API route not found")
    index_file = FRONTEND_DIST / "index.html"
    if index_file.exists():
        return FileResponse(
            str(index_file),
            headers={"Cache-Control": "no-cache, no-store, must-revalidate"}
        )
    return HTMLResponse("<h1>FinPilot AI backend is active. React frontend is building...</h1>")
