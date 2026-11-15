"""Inject custom CSS styles for the FinPilot AI terminal theme."""
import os
import streamlit as st
from pathlib import Path


def apply_styles():
    """Load and inject custom dark financial terminal CSS."""
    css_path = Path(__file__).parent / "styles.css"
    if css_path.exists():
        with open(css_path, "r", encoding="utf-8") as f:
            css_content = f.read()
        st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)
    else:
        # Fallback inline styles
        st.markdown("""<style>
        .stApp {background:#0a0f1d;color:#f0f4fc;}
        [data-testid="stSidebar"] {background:#111a2e;border-right:1px solid #243654;}
        [data-testid="stMetric"] {background:#162238;border:1px solid #243654;padding:16px;border-radius:12px;}
        h1,h2,h3 {color:#f8fafc;}
        .stButton>button {border-radius:8px;font-weight:600;}
        </style>""", unsafe_allow_html=True)
