"""FinPilot AI — Root Entrypoint Redirect.
Ensures seamless deployment regardless of whether Streamlit Cloud is configured
with 'streamlit_app.py', 'app.py', or 'FinPilot-AI/app.py'.
"""
from pathlib import Path
import runpy

ROOT_DIR = Path(__file__).resolve().parent
ENTRYPOINT = ROOT_DIR / "streamlit_app.py"

runpy.run_path(str(ENTRYPOINT), run_name="__main__")
