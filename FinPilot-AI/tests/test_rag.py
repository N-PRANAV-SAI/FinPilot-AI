"""Unit tests for RAG text splitting and document chunking."""
import pytest
from backend.rag.text_splitter import split_documents


def test_splitter_preserves_metadata():
    """Verify that split_documents preserves parent metadata and assigns chunk_ids."""
    docs = [
        {
            "text": "This is a long financial disclosure report section. " * 30,
            "metadata": {"ticker": "NVDA", "document_title": "10-K Annual Report", "filing_date": "2024-02-21"},
        }
    ]

    chunks = split_documents(docs, chunk_size=500, overlap=50)

    assert len(chunks) >= 2
    for i, chunk in enumerate(chunks):
        assert chunk["metadata"]["ticker"] == "NVDA"
        assert chunk["metadata"]["document_title"] == "10-K Annual Report"
        assert chunk["metadata"]["chunk_id"] == i
        assert len(chunk["text"]) > 0


def test_splitter_handles_empty_input():
    """Verify that empty document list yields empty chunk list."""
    assert split_documents([]) == []
    assert split_documents([{"text": "   ", "metadata": {}}]) == []
