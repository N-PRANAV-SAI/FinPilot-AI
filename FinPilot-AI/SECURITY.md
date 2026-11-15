# FinPilot AI — Security Architecture & Data Protection Policy

This document outlines the security controls, credential protection mechanisms, and data isolation policies implemented in **FinPilot AI**.

---

## 🔒 1. Credential & Secret Protection

### A. Zero Secrets in Version Control
- All API keys (Google Gemini, Finnhub, EODHD, FMP) and database connection strings are managed strictly through environment variables (`.env`) or Streamlit Cloud Secrets (`st.secrets`).
- `.gitignore` rigorously excludes all `.env` files, `.streamlit/secrets.toml`, and local SQLite databases.
- Example templates with non-functional placeholders (`.env.example` and `secrets.toml.example`) are provided for developer setup.

### B. Dynamic Runtime Secrets Bridge
The deployment entrypoint (`streamlit_app.py`) dynamically bridges `st.secrets` into the Python runtime environment without writing sensitive credentials to disk or serializing them to client-side assets.

---

## 👤 2. Authentication & User Data Isolation

### A. Password Hashing
- User passwords are never stored in plaintext. Passwords are cryptographic hashes stored within the `users` table in `database/models.py`.
- Session tokens are maintained securely in server-side session state (`st.session_state`).

### B. User-Level Relational Isolation
- All virtual accounts, portfolio holdings, orders, and transactions carry an explicit foreign key reference to `user_id`.
- Every database query strictly filters by the authenticated user's ID:
  ```python
  holdings = db.query(Holdings).filter(Holdings.user_id == authenticated_user_id).all()
  ```
- Cross-user data leakage is strictly prevented at the ORM layer.

---

## 🛡️ 3. Input Validation & Injection Prevention

### A. SQL Injection Prevention
- All database interactions use SQLAlchemy 2.0 object-relational mapping with parameterized statements. Raw SQL string concatenation is strictly prohibited.

### B. Ticker Format Validation
- Asset symbols are validated using a strict regex whitelist preventing path traversal or shell injection:
  ```python
  TICKER_REGEX = re.compile(r"^[\^]?[A-Za-z0-9\.\-\=]{1,30}$")
  ```

---

## 🚫 4. Virtual Trading Safety Guarantees

FinPilot AI is built strictly as an educational and quantitative research platform:
1. **Zero Brokerage Connectivity**: The platform has no integration with real brokerage accounts (Interactive Brokers, Alpaca, Zerodha, Robinhood, etc.).
2. **No Real Money Execution**: It is impossible for any user, script, or model in FinPilot AI to execute a real financial transaction.
3. **No Automatic Trades**: All simulated paper orders require explicit user confirmation.

---

## ⚠️ 5. Known Limitations & Recommendations

1. **Ephemeral Cloud Storage**: SQLite on free-tier Streamlit Community Cloud resets during container cold starts. For persistent multi-user production deployments, configure a managed cloud PostgreSQL database (such as Supabase or Neon) via `DATABASE_URL`.
2. **Offline Baseline Fallback**: When external market APIs are unreachable or offline, the platform provides a deterministic synthetic market series explicitly flagged with a `SIMULATED_DEMO` badge to prevent confusing simulated data with live exchange prices.
