"""SQLAlchemy ORM models for FinPilot AI."""
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Index, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from database.db import Base
import hashlib


class Company(Base):
    __tablename__ = "companies"
    company_id = Column(Integer, primary_key=True)
    company_name = Column(String(200), nullable=False)
    ticker = Column(String(30), unique=True, index=True, nullable=False)
    sector = Column(String(120))
    industry = Column(String(120))
    country = Column(String(80))
    exchange = Column(String(50))
    currency = Column(String(20))


class MarketData(Base):
    __tablename__ = "market_data"
    id = Column(Integer, primary_key=True)
    ticker = Column(String(30), index=True, nullable=False)
    date = Column(DateTime, nullable=False)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    adjusted_close = Column(Float)
    volume = Column(Float)
    currency = Column(String(20))
    __table_args__ = (Index("ix_market_ticker_date", "ticker", "date", unique=True),)


class Prediction(Base):
    __tablename__ = "predictions"
    prediction_id = Column(Integer, primary_key=True)
    ticker = Column(String(30), index=True)
    prediction_date = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    prediction_horizon = Column(Integer, default=5)
    predicted_class = Column(Integer)
    predicted_probability = Column(Float)
    selected_model = Column(String(100))
    exchange = Column(String(50))
    currency = Column(String(20))


class ModelMetrics(Base):
    __tablename__ = "model_metrics"
    id = Column(Integer, primary_key=True)
    model_name = Column(String(100))
    ticker = Column(String(30), index=True)
    training_date = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    accuracy = Column(Float)
    precision = Column(Float)
    recall = Column(Float)
    f1_score = Column(Float)
    roc_auc = Column(Float)
    dataset_type = Column(String(20))  # 'quantitative' or 'hybrid'


class SentimentAnalysis(Base):
    __tablename__ = "sentiment_analysis"
    sentiment_id = Column(Integer, primary_key=True)
    ticker = Column(String(30), index=True)
    news_title = Column(Text)
    publication_date = Column(DateTime)
    sentiment_label = Column(String(20))
    positive_score = Column(Float)
    negative_score = Column(Float)
    neutral_score = Column(Float)
    source_url = Column(Text)


class Document(Base):
    __tablename__ = "documents"
    document_id = Column(Integer, primary_key=True)
    ticker = Column(String(30), index=True)
    document_name = Column(Text)
    document_type = Column(String(50))
    country = Column(String(80))
    exchange = Column(String(50))
    filing_date = Column(DateTime)
    source_url = Column(Text)


class AnalysisHistory(Base):
    __tablename__ = "analysis_history"
    analysis_id = Column(Integer, primary_key=True)
    ticker = Column(String(30), index=True)
    company_name = Column(String(200))
    country = Column(String(80))
    exchange = Column(String(50))
    currency = Column(String(20))
    analysis_date = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    prediction_summary = Column(Text)
    sentiment_summary = Column(Text)
    selected_model = Column(String(100))
    llm_explanation = Column(Text)


# =========================================================================
# VIRTUAL INVESTING, USER ONBOARDING & LEARNING SCHEMA
# =========================================================================

class User(Base):
    __tablename__ = "users"
    user_id = Column(Integer, primary_key=True)
    name = Column(String(150), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    experience_level = Column(String(50), default="Beginner")  # Beginner, Intermediate, Advanced
    learning_goals = Column(Text, default="Learn how the stock market works, Practise investing")  # Comma-separated or JSON
    risk_comfort = Column(String(50), default="Moderate")  # Low, Moderate, High, Not sure yet
    preferred_currency = Column(String(20), default="INR")  # INR, USD, EUR, GBP
    preferred_mode = Column(String(50), default="Beginner learning mode")  # Beginner, Normal, Advanced
    onboarding_completed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    virtual_account = relationship("VirtualAccount", back_populates="user", uselist=False, cascade="all, delete-orphan")
    portfolio = relationship("Portfolio", back_populates="user", uselist=False, cascade="all, delete-orphan")
    holdings = relationship("Holdings", back_populates="user", cascade="all, delete-orphan")
    orders = relationship("VirtualOrders", back_populates="user", cascade="all, delete-orphan")
    transactions = relationship("VirtualTransactions", back_populates="user", cascade="all, delete-orphan")


class VirtualAccount(Base):
    __tablename__ = "virtual_accounts"
    account_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False, unique=True, index=True)
    initial_virtual_balance = Column(Float, default=100000.0)
    available_cash = Column(Float, default=100000.0)
    account_currency = Column(String(20), default="INR")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="virtual_account")


class Portfolio(Base):
    __tablename__ = "portfolios"
    portfolio_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False, unique=True, index=True)
    total_value = Column(Float, default=100000.0)
    invested_value = Column(Float, default=0.0)
    cash_balance = Column(Float, default=100000.0)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="portfolio")


class Holdings(Base):
    __tablename__ = "holdings"
    holding_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.portfolio_id"), nullable=True)
    company_id = Column(Integer, nullable=True)
    company_name = Column(String(200), default="")
    ticker = Column(String(30), nullable=False, index=True)
    exchange = Column(String(50), default="US")
    country = Column(String(80), default="United States")
    quantity = Column(Float, nullable=False, default=0.0)
    average_cost = Column(Float, nullable=False, default=0.0)  # In asset trading currency
    currency = Column(String(20), default="USD")

    user = relationship("User", back_populates="holdings")


class VirtualOrders(Base):
    __tablename__ = "virtual_orders"
    order_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False, index=True)
    company_id = Column(Integer, nullable=True)
    company_name = Column(String(200), default="")
    ticker = Column(String(30), nullable=False, index=True)
    exchange = Column(String(50), default="")
    currency = Column(String(20), default="USD")
    order_type = Column(String(20), default="MARKET")  # MARKET, LIMIT
    side = Column(String(10), nullable=False)  # BUY, SELL
    quantity = Column(Float, nullable=False)
    limit_price = Column(Float, nullable=True)
    execution_price = Column(Float, nullable=True)
    order_status = Column(String(20), default="EXECUTED")  # PENDING, EXECUTED, CANCELLED, REJECTED
    rejection_reason = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    executed_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="orders")


class VirtualTransactions(Base):
    __tablename__ = "virtual_transactions"
    transaction_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False, index=True)
    order_id = Column(Integer, ForeignKey("virtual_orders.order_id"), nullable=True)
    ticker = Column(String(30), nullable=False)
    company_name = Column(String(200), default="")
    transaction_type = Column(String(10), nullable=False)  # BUY, SELL, DEPOSIT, RESET
    quantity = Column(Float, nullable=False, default=0.0)
    price = Column(Float, nullable=False, default=0.0)
    fees = Column(Float, default=0.0)
    total_amount = Column(Float, nullable=False)  # Total in user's account currency
    currency = Column(String(20), default="INR")
    realized_pnl = Column(Float, default=0.0)
    transaction_date = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="transactions")


class OnboardingPreferences(Base):
    __tablename__ = "onboarding_preferences"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False, unique=True, index=True)
    experience_level = Column(String(50))
    learning_goals = Column(Text)
    risk_comfort = Column(String(50))
    currency = Column(String(20))
    selected_practice_balance = Column(Float)
    learning_mode = Column(String(50))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class Watchlist(Base):
    __tablename__ = "watchlist"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False, index=True)
    company_id = Column(Integer, nullable=True)
    ticker = Column(String(30), nullable=False)
    company_name = Column(String(200))
    exchange = Column(String(50))
    country = Column(String(80))
    currency = Column(String(20))
    added_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class LearningProgress(Base):
    __tablename__ = "learning_progress"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False, index=True)
    lesson_id = Column(String(100), nullable=False)
    completion_status = Column(Boolean, default=False)
    quiz_score = Column(Float, default=0.0)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
