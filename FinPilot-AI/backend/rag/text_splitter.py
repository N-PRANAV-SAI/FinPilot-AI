"""Text chunking for RAG pipelines."""
import logging

log = logging.getLogger(__name__)


def split_documents(docs: list[dict], chunk_size: int = 1000, overlap: int = 150) -> list[dict]:
    """Split documents into overlapping chunks with preserved metadata.
    
    Each chunk inherits all metadata from its parent document and receives
    a unique 'chunk_id'.
    
    Args:
        docs: List of dicts with 'text' and 'metadata'.
        chunk_size: Target character length per chunk.
        overlap: Character overlap between consecutive chunks.
        
    Returns:
        List of chunk dicts ready for embedding.
    """
    chunks = []
    for doc in docs:
        text = doc.get("text", "")
        meta = doc.get("metadata", {})
        start = 0
        idx = 0

        while start < len(text):
            end = min(len(text), start + chunk_size)

            # Try to snap to sentence or paragraph boundary if not at end
            if end < len(text):
                for sep in ("\n\n", ".\n", ". ", "; ", "\n", " "):
                    last_sep = text[start:end].rfind(sep)
                    if last_sep > chunk_size * 0.5:
                        end = start + last_sep + len(sep)
                        break

            chunk_text = text[start:end].strip()
            if chunk_text:
                chunks.append({
                    "text": chunk_text,
                    "metadata": {
                        **meta,
                        "chunk_id": idx,
                    },
                })
                idx += 1

            if end >= len(text):
                break
            start = max(0, end - overlap)

    log.info("Split %d documents into %d chunks (chunk_size=%d, overlap=%d).", len(docs), len(chunks), chunk_size, overlap)
    return chunks
