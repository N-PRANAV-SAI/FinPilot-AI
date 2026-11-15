"""Model persistence and loading."""
import os
import logging
import joblib
from config.settings import settings

log = logging.getLogger(__name__)


def load_model(ticker: str) -> dict | None:
    """Load a saved model bundle for the given ticker."""
    path = os.path.join(settings.model_dir, f"{ticker.upper()}_model.joblib")
    if not os.path.exists(path):
        log.info("No saved model found for %s", ticker)
        return None
    bundle = joblib.load(path)
    log.info("Loaded model for %s: %s", ticker, bundle.get("selected_model"))
    return bundle


def save_model(bundle: dict, ticker: str) -> str:
    """Save a model bundle and return the file path."""
    os.makedirs(settings.model_dir, exist_ok=True)
    path = os.path.join(settings.model_dir, f"{ticker.upper()}_model.joblib")
    joblib.dump(bundle, path)
    log.info("Saved model for %s to %s", ticker, path)
    return path
