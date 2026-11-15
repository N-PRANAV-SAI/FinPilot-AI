"""Authentication and User Profile Management Service for FinPilot AI."""
import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List
import jwt
from sqlalchemy.orm import Session
from database.models import User, VirtualAccount, Portfolio, OnboardingPreferences

JWT_SECRET = os.getenv("JWT_SECRET", "finpilot-super-secret-key-2026-production-secure-32bytes")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 72


def hash_password(password: str) -> str:
    """Hash password using salt + sha256 for cross-platform reliability without external C extensions."""
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000)
    return f"{salt}:{key.hex()}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify stored salted hash."""
    try:
        salt, key_hex = hashed_password.split(":")
        new_key = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt.encode("utf-8"), 100000)
        return secrets.compare_digest(new_key.hex(), key_hex)
    except Exception:
        return False


def create_access_token(user_id: int, email: str) -> str:
    """Create a signed JWT access token."""
    expire = datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS)
    payload = {
        "sub": str(user_id),
        "email": email,
        "exp": expire
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and validate a JWT access token."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except Exception:
        return None


def register_user(name: str, email: str, password: str, db: Session) -> Dict[str, Any]:
    """Register a new user and initialize their virtual investing account."""
    clean_email = email.strip().lower()
    existing = db.query(User).filter(User.email == clean_email).first()
    if existing:
        return {"success": False, "error": "An account with this email already exists."}
    
    if len(password) < 6:
        return {"success": False, "error": "Password must be at least 6 characters long."}

    user = User(
        name=name.strip(),
        email=clean_email,
        password_hash=hash_password(password),
        experience_level="Beginner",
        preferred_currency="INR",
        preferred_mode="Beginner learning mode",
        onboarding_completed=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Initialize default virtual account & portfolio (₹1,00,000 / $10,000 default)
    v_acc = VirtualAccount(
        user_id=user.user_id,
        initial_virtual_balance=100000.0,
        available_cash=100000.0,
        account_currency="INR"
    )
    port = Portfolio(
        user_id=user.user_id,
        total_value=100000.0,
        invested_value=0.0,
        cash_balance=100000.0
    )
    db.add(v_acc)
    db.add(port)
    db.commit()

    token = create_access_token(user.user_id, user.email)
    return {
        "success": True,
        "token": token,
        "user": {
            "user_id": user.user_id,
            "name": user.name,
            "email": user.email,
            "experience_level": user.experience_level,
            "preferred_currency": user.preferred_currency,
            "onboarding_completed": False
        }
    }


def authenticate_user(email: str, password: str, db: Session) -> Dict[str, Any]:
    """Authenticate an existing user."""
    clean_email = email.strip().lower()
    user = db.query(User).filter(User.email == clean_email).first()
    if not user or not verify_password(password, user.password_hash):
        return {"success": False, "error": "Invalid email or password."}

    token = create_access_token(user.user_id, user.email)
    return {
        "success": True,
        "token": token,
        "user": {
            "user_id": user.user_id,
            "name": user.name,
            "email": user.email,
            "experience_level": user.experience_level,
            "preferred_currency": user.preferred_currency,
            "preferred_mode": user.preferred_mode,
            "risk_comfort": user.risk_comfort,
            "learning_goals": user.learning_goals,
            "onboarding_completed": user.onboarding_completed
        }
    }


def save_onboarding_preferences(
    user_id: int,
    experience_level: str,
    learning_goals: List[str],
    risk_comfort: str,
    preferred_currency: str,
    practice_balance: float,
    trading_mode: str,
    db: Session
) -> Dict[str, Any]:
    """Save user onboarding answers and set their initial virtual funds."""
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        return {"success": False, "error": "User not found."}

    goals_str = ", ".join(learning_goals) if isinstance(learning_goals, list) else str(learning_goals)

    user.experience_level = experience_level
    user.learning_goals = goals_str
    user.risk_comfort = risk_comfort
    user.preferred_currency = preferred_currency
    user.preferred_mode = trading_mode
    user.onboarding_completed = True

    # Update or create VirtualAccount
    v_acc = db.query(VirtualAccount).filter(VirtualAccount.user_id == user_id).first()
    if not v_acc:
        v_acc = VirtualAccount(user_id=user_id)
        db.add(v_acc)
    v_acc.initial_virtual_balance = practice_balance
    v_acc.available_cash = practice_balance
    v_acc.account_currency = preferred_currency

    # Update or create Portfolio
    port = db.query(Portfolio).filter(Portfolio.user_id == user_id).first()
    if not port:
        port = Portfolio(user_id=user_id)
        db.add(port)
    port.total_value = practice_balance
    port.cash_balance = practice_balance
    port.invested_value = 0.0

    # Save preferences record
    pref = db.query(OnboardingPreferences).filter(OnboardingPreferences.user_id == user_id).first()
    if not pref:
        pref = OnboardingPreferences(user_id=user_id)
        db.add(pref)
    pref.experience_level = experience_level
    pref.learning_goals = goals_str
    pref.risk_comfort = risk_comfort
    pref.currency = preferred_currency
    pref.selected_practice_balance = practice_balance
    pref.learning_mode = trading_mode

    db.commit()
    return {"success": True, "message": "Onboarding completed successfully."}
