"""Embedding service for vector search in RAG pipeline."""
import logging
from config.settings import settings

log = logging.getLogger(__name__)


class EmbeddingService:
    """Generates normalized vector embeddings using Sentence Transformers."""

    def __init__(self):
        self._model = None

    def _load(self):
        """Lazy-load the SentenceTransformer embedding model."""
        if self._model is None:
            log.info("Loading embedding model: %s", settings.embedding_model)
            try:
                import os
                from pathlib import Path
                from sentence_transformers import SentenceTransformer
                from backend.data.providers.yfinance_provider import is_dns_online

                # Check for cached snapshot path directly
                cache_dir = Path.home() / ".cache" / "huggingface" / "hub" / "models--sentence-transformers--all-MiniLM-L6-v2" / "snapshots"
                local_path = None
                if cache_dir.exists():
                    subdirs = [p for p in cache_dir.iterdir() if p.is_dir()]
                    if subdirs:
                        local_path = str(subdirs[0])

                if not is_dns_online():
                    os.environ["HF_HUB_OFFLINE"] = "1"

                model_target = local_path if local_path else settings.embedding_model
                self._model = SentenceTransformer(model_target)
                log.info("Embedding model loaded successfully from %s", model_target)
            except Exception as exc:
                log.error("Failed to load embedding model: %s", exc)
                raise RuntimeError(
                    f"SentenceTransformer model ({settings.embedding_model}) could not be loaded: {exc}."
                ) from exc

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate normalized embeddings for a list of text strings.
        
        Args:
            texts: List of strings to encode.
            
        Returns:
            List of embedding vectors (list of floats).
        """
        if not texts:
            return []
        self._load()
        embeddings = self._model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=False,
            batch_size=32,
        )
        return embeddings.tolist()
