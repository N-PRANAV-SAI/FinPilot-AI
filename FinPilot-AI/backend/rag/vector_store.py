"""Persistent vector storage with ChromaDB for RAG."""
import os
import logging
import chromadb
from config.settings import settings
from backend.rag.embedding_service import EmbeddingService

log = logging.getLogger(__name__)


class VectorStore:
    """Persistent vector store backed by ChromaDB and SentenceTransformer embeddings."""

    def __init__(self):
        os.makedirs(settings.chroma_dir, exist_ok=True)
        self.client = chromadb.PersistentClient(path=settings.chroma_dir)
        self.collection = self.client.get_or_create_collection(
            name="finpilot_evidence",
            metadata={"hnsw:space": "cosine"},
        )
        self.embedder = EmbeddingService()

    def add(self, chunks: list[dict], ticker: str) -> int:
        """Embed and upsert document chunks into the collection.
        
        Args:
            chunks: List of dicts with 'text' and 'metadata'.
            ticker: Stock ticker symbol.
            
        Returns:
            Number of chunks successfully added.
        """
        if not chunks:
            return 0

        texts = [x["text"] for x in chunks]
        vectors = self.embedder.embed(texts)

        ids = []
        metadatas = []
        clean_texts = []

        for i, chunk in enumerate(chunks):
            chunk_meta = chunk.get("metadata", {})
            doc_id = str(chunk_meta.get("document_id") or chunk_meta.get("form") or "doc")
            chunk_idx = str(chunk_meta.get("chunk_id", i))
            c_id = f"{ticker.upper()}_{doc_id}_{chunk_idx}_{i}"
            ids.append(c_id)

            # ChromaDB requires metadata values to be str, int, float, or bool
            meta = {"ticker": ticker.upper()}
            for k, v in chunk_meta.items():
                if v is None:
                    meta[k] = ""
                elif isinstance(v, (str, int, float, bool)):
                    meta[k] = v
                else:
                    meta[k] = str(v)
            metadatas.append(meta)
            clean_texts.append(chunk["text"])

        # Batch upsert in chunks of 100 to avoid payload size issues
        batch_size = 100
        for b in range(0, len(ids), batch_size):
            self.collection.upsert(
                ids=ids[b:b + batch_size],
                documents=clean_texts[b:b + batch_size],
                metadatas=metadatas[b:b + batch_size],
                embeddings=vectors[b:b + batch_size],
            )

        log.info("Indexed %d chunks for %s into ChromaDB collection.", len(ids), ticker)
        return len(ids)

    def query(self, question: str, ticker: str, n_results: int = 5) -> list[dict]:
        """Retrieve the most semantically relevant evidence passages.
        
        Args:
            question: Search query or user research question.
            ticker: Stock ticker to filter evidence for.
            n_results: Maximum number of passages to return.
            
        Returns:
            List of dicts with 'text', 'metadata', and 'distance'.
        """
        if self.collection.count() == 0:
            log.info("ChromaDB collection is empty.")
            return []

        query_vectors = self.embedder.embed([question])
        if not query_vectors:
            return []

        # Query with ticker filter first
        try:
            res = self.collection.query(
                query_embeddings=query_vectors,
                n_results=min(n_results, self.collection.count()),
                where={"ticker": ticker.upper()},
            )
        except Exception as exc:
            log.warning("Filtered query failed (%s); trying unfiltered query.", exc)
            res = self.collection.query(
                query_embeddings=query_vectors,
                n_results=min(n_results, self.collection.count()),
            )

        out = []
        if res.get("documents") and res["documents"][0]:
            for doc, meta, distance in zip(
                res["documents"][0],
                res["metadatas"][0],
                res["distances"][0],
            ):
                out.append({
                    "text": doc,
                    "metadata": meta,
                    "distance": float(distance),
                    "relevance_score": max(0.0, 1.0 - float(distance)),
                })

        log.info("Retrieved %d relevant evidence chunks for '%s'.", len(out), question[:60])
        return out

    def get_stats(self, ticker: str | None = None) -> dict:
        """Return total chunk count and indexed document info."""
        total = self.collection.count()
        return {"total_chunks": total}
