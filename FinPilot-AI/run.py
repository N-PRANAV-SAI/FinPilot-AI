"""FinPilot AI Launcher (Nested)."""
import subprocess
import sys
from pathlib import Path

if __name__ == "__main__":
    PROJECT_DIR = Path(__file__).resolve().parent
    cmd = [sys.executable, "-m", "uvicorn", "backend.api.main:app", "--host", "127.0.0.1", "--port", "8000"]
    raise SystemExit(subprocess.call(cmd, cwd=str(PROJECT_DIR)))
