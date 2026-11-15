"""FinPilot AI Launcher — FastAPI + React Platform.

Usage:
    python run.py             # Launches FastAPI + React application on http://localhost:8000
    python run.py --streamlit # Launches legacy Streamlit dashboard on http://localhost:8501
"""
import os
import sys
import argparse
import subprocess
from pathlib import Path

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FinPilot AI Application Launcher")
    parser.add_argument("--port", type=int, default=8000, help="Port to run FastAPI on (default: 8000)")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host interface (default: 127.0.0.1)")
    parser.add_argument("--streamlit", action="store_true", help="Launch Streamlit instead of FastAPI + React")
    args = parser.parse_args()

    PROJECT_DIR = Path(__file__).resolve().parent / "FinPilot-AI"
    if not PROJECT_DIR.exists():
        PROJECT_DIR = Path(__file__).resolve().parent

    venv_python = PROJECT_DIR / ".venv" / "Scripts" / "python.exe"
    python_exec = str(venv_python) if venv_python.exists() else sys.executable

    env = os.environ.copy()
    env["PYTHONPATH"] = str(PROJECT_DIR)

    if args.streamlit:
        app_path = PROJECT_DIR / "app.py"
        print(f"◈ Starting FinPilot AI Streamlit Dashboard...")
        print(f"◈ URL: http://localhost:8501\n")
        cmd = [python_exec, "-m", "streamlit", "run", str(app_path)]
    else:
        print(f"◈ ===================================================")
        print(f"◈ FinPilot AI — Global Investing & AI Mentorship")
        print(f"◈ FastAPI REST API & React Frontend Platform")
        print(f"◈ URL: http://localhost:{args.port} (or http://{args.host}:{args.port})")
        print(f"◈ Using Python: {python_exec}")
        print(f"◈ ===================================================\n")
        cmd = [
            python_exec, "-m", "uvicorn",
            "backend.api.main:app",
            "--host", args.host,
            "--port", str(args.port),
            "--app-dir", str(PROJECT_DIR)
        ]

    try:
        raise SystemExit(subprocess.call(cmd, cwd=str(PROJECT_DIR), env=env))
    except KeyboardInterrupt:
        print("\n◈ FinPilot AI server stopped.")
