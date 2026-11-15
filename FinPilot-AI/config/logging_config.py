"""Centralized logging configuration."""
import logging
import os
from config.settings import settings


def configure_logging():
    os.makedirs(settings.log_dir, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        handlers=[
            logging.FileHandler(os.path.join(settings.log_dir, "finpilot.log")),
            logging.StreamHandler(),
        ],
    )
    # Suppress noisy third-party loggers
    for name in ("httpx", "chromadb", "urllib3", "transformers", "sentence_transformers"):
        logging.getLogger(name).setLevel(logging.WARNING)
