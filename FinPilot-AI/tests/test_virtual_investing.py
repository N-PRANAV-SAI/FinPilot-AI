"""Unit tests for FinPilot AI Virtual Investing, User Onboarding, and AI Assistant."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.db import Base
from database.models import User, VirtualAccount, Portfolio, Holdings, VirtualOrders, VirtualTransactions
from backend.services.auth_service import (
    register_user, authenticate_user, save_onboarding_preferences, hash_password, verify_password
)
from backend.trading.paper_engine import PaperTradingEngine, get_fx_rate
from backend.education.learning_center import LearningCenterService
from backend.assistant.ai_assistant import FinPilotAIAssistant


@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_password_hashing():
    pwd = "SecurePassword123!"
    h = hash_password(pwd)
    assert verify_password(pwd, h) is True
    assert verify_password("WrongPassword", h) is False


def test_user_registration_and_auth(test_db):
    res = register_user("Pranav Sharma", "pranav@finpilot.ai", "Password123!", test_db)
    assert res["success"] is True
    user_id = res["user"]["user_id"]

    # Test duplicate prevention
    dup = register_user("Pranav Duplicate", "pranav@finpilot.ai", "Password123!", test_db)
    assert dup["success"] is False

    # Test authentication
    auth_ok = authenticate_user("pranav@finpilot.ai", "Password123!", test_db)
    assert auth_ok["success"] is True
    assert auth_ok["user"]["user_id"] == user_id

    auth_fail = authenticate_user("pranav@finpilot.ai", "WrongPass", test_db)
    assert auth_fail["success"] is False


def test_onboarding_preferences(test_db):
    res = register_user("Jane Doe", "jane@finpilot.ai", "Secret123", test_db)
    user_id = res["user"]["user_id"]

    onb = save_onboarding_preferences(
        user_id=user_id,
        experience_level="Beginner",
        learning_goals=["Learn how the stock market works", "Practise investing"],
        risk_comfort="Low",
        preferred_currency="USD",
        practice_balance=50000.0,
        trading_mode="Beginner learning mode",
        db=test_db
    )
    assert onb["success"] is True

    summary = PaperTradingEngine.get_user_account_summary(user_id, test_db)
    assert summary["account_currency"] == "USD"
    assert summary["available_cash"] == 50000.0
    assert summary["total_portfolio_value"] == 50000.0


def test_paper_trading_buy_and_sell(test_db, monkeypatch):
    # Mock get_latest_price to return deterministic test quote
    def mock_get_latest_price(ticker):
        return {"ticker": ticker, "price": 100.0, "currency": "USD", "change": 1.5, "change_pct": 1.5}

    import backend.trading.paper_engine as pe
    monkeypatch.setattr(pe, "get_latest_price", mock_get_latest_price)

    res = register_user("Trader Bob", "bob@finpilot.ai", "BobPass123", test_db)
    user_id = res["user"]["user_id"]

    # Initial balance is 100,000 INR
    # Buy 1 share of AAPL at $100. In INR with fx 86.2, total is ~8,620.69 INR
    buy_res = PaperTradingEngine.execute_buy_order(
        user_id=user_id,
        ticker="AAPL",
        company_name="Apple Inc.",
        exchange="NASDAQ",
        country="United States",
        currency="USD",
        order_type="MARKET",
        quantity=2.0,
        db=test_db
    )
    assert buy_res["success"] is True
    assert buy_res["quantity"] == 2.0
    assert buy_res["remaining_cash"] < 100000.0

    # Verify summary has holding
    summary = PaperTradingEngine.get_user_account_summary(user_id, test_db)
    assert len(summary["holdings"]) == 1
    assert summary["holdings"][0]["ticker"] == "AAPL"

    # Sell 1 share
    sell_res = PaperTradingEngine.execute_sell_order(
        user_id=user_id,
        ticker="AAPL",
        quantity=1.0,
        db=test_db
    )
    assert sell_res["success"] is True
    assert sell_res["remaining_quantity"] == 1.0


def test_account_reset(test_db):
    res = register_user("Reset User", "reset@finpilot.ai", "Reset123", test_db)
    user_id = res["user"]["user_id"]

    reset_res = PaperTradingEngine.reset_virtual_account(user_id, 250000.0, test_db)
    assert reset_res["success"] is True
    assert reset_res["new_cash_balance"] == 250000.0


def test_learning_center_quizzes(test_db):
    res = register_user("Student", "student@finpilot.ai", "Pass123", test_db)
    user_id = res["user"]["user_id"]

    lessons = LearningCenterService.get_all_lessons(user_id, test_db)
    assert len(lessons) >= 8

    # Lesson 1 correct answer is index 1
    quiz_res = LearningCenterService.submit_quiz_answer(
        user_id=user_id,
        lesson_id="lesson_1",
        selected_option_index=1,
        db=test_db
    )
    assert quiz_res["success"] is True
    assert quiz_res["is_correct"] is True


def test_ai_assistant_fallback():
    assistant = FinPilotAIAssistant()
    assistant.llm.is_available = lambda: False
    profile = {"name": "Pranav", "experience_level": "Beginner", "preferred_currency": "INR"}
    
    # Test glossary lookup
    reply = assistant.generate_response("What does RSI mean?", profile)
    assert "Relative Strength Index" in reply
