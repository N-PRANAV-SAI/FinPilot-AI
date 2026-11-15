"""FinPilot AI — Streamlit Community Cloud Deployment Entrypoint.

Bridges Streamlit Secrets (st.secrets) to application configuration,
configures page metadata, and mounts the complete FinPilot AI terminal.
"""
import os
import sys
from pathlib import Path

# Ensure application directories are on python search path
CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

# Ensure child directory is on path if executing from parent
INNER_APP_DIR = CURRENT_DIR / "FinPilot-AI"
if INNER_APP_DIR.exists() and str(INNER_APP_DIR) not in sys.path:
    sys.path.insert(0, str(INNER_APP_DIR))

# Bridge Streamlit Cloud Secrets into environment variables before any module loads
try:
    import streamlit as st
    if hasattr(st, "secrets"):
        for secret_key, val in st.secrets.items():
            if isinstance(val, (str, int, float, bool)) and not os.getenv(secret_key):
                os.environ[secret_key] = str(val)
except Exception:
    pass

# Execute the primary Streamlit application
import app
