"""High-level retriever for financial document RAG."""
import logging
from backend.rag.vector_store import VectorStore
from backend.rag.text_splitter import split_documents
from backend.rag.document_loader import load_pdf, load_sec_filing

log = logging.getLogger(__name__)


class FinancialRetriever:
    """Manages document ingestion, chunking, and semantic evidence retrieval."""

    def __init__(self):
        self.store = VectorStore()

    def ingest(self, docs: list[dict], ticker: str, document_metadata: dict | None = None) -> int:
        """Split and ingest document pages or sections into the vector store.
        
        Args:
            docs: List of dicts with 'text' and 'metadata'.
            ticker: Stock ticker to associate with.
            document_metadata: Extra metadata (e.g. document_title, filing_date).
            
        Returns:
            Number of chunks indexed.
        """
        enriched = []
        for d in docs:
            combined_meta = {
                **(document_metadata or {}),
                **d.get("metadata", {}),
                "ticker": ticker.upper(),
            }
            enriched.append({
                "text": d["text"],
                "metadata": combined_meta,
            })

        chunks = split_documents(enriched, chunk_size=1000, overlap=150)
        count = self.store.add(chunks, ticker.upper())
        log.info("Successfully ingested %d chunks for %s.", count, ticker)
        return count

    def ingest_sec_filing(self, url: str, ticker: str, metadata: dict | None = None) -> int:
        """Download an SEC filing from URL and ingest it into the vector store.
        
        Args:
            url: SEC EDGAR document URL.
            ticker: Stock ticker.
            metadata: Filing metadata (form, date, title, etc.).
            
        Returns:
            Number of chunks indexed.
        """
        docs = load_sec_filing(url, metadata)
        if not docs:
            return 0
        return self.ingest(docs, ticker, metadata)

    def retrieve(self, question: str, ticker: str, k: int = 5) -> list[dict]:
        """Retrieve the top-k most relevant evidence passages for a query.
        
        Args:
            question: Search query or user research question.
            ticker: Target stock ticker.
            k: Maximum number of passages to retrieve.
            
        Returns:
            List of evidence dictionaries with text, metadata, and relevance score.
        """
        return self.store.query(question, ticker.upper(), n_results=k)

    def get_stats(self) -> dict:
        """Return vector store statistics."""
        return self.store.get_stats()
