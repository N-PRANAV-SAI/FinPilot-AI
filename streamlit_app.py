"""FinPilot AI — Streamlit Community Cloud Deployment Entrypoint.

Bridges Streamlit Secrets (st.secrets) to application configuration,
configures page metadata, and mounts the complete FinPilot AI terminal.
"""
import os
import sys
import runpy
from pathlib import Path

# Ensure application directories are on python search path
CURRENT_DIR = Path(__file__).resolve().parent
INNER_APP_DIR = CURRENT_DIR / "FinPilot-AI"

target_dir = INNER_APP_DIR if INNER_APP_DIR.exists() else CURRENT_DIR
if str(target_dir) not in sys.path:
    sys.path.insert(0, str(target_dir))
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

os.chdir(str(target_dir))

# Bridge Streamlit Cloud Secrets into environment variables before any module loads
try:
    import streamlit as st
    if hasattr(st, "secrets"):
        for secret_key, val in st.secrets.items():
            if isinstance(val, (str, int, float, bool)) and not os.getenv(secret_key):
                os.environ[secret_key] = str(val)
except Exception:
    pass

app_file = target_dir / "app.py"
runpy.run_path(str(app_file), run_name="__main__")
