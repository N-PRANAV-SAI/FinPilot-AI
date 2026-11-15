"""Document ingestion and loading for RAG."""
import logging
import requests
from io import BytesIO
from config.settings import settings

log = logging.getLogger(__name__)


def load_pdf(path_or_file, metadata: dict | None = None) -> list[dict]:
    """Extract page text from a PDF document.
    
    Args:
        path_or_file: File path string or file-like object (BytesIO).
        metadata: Optional dictionary with document attributes.
        
    Returns:
        List of dicts, each with 'text' and 'metadata'.
    """
    from pypdf import PdfReader

    try:
        reader = PdfReader(path_or_file)
        docs = []
        for i, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            text = " ".join(text.split())  # Clean excessive whitespace
            if text.strip():
                docs.append({
                    "text": text,
                    "metadata": {
                        **(metadata or {}),
                        "page": i + 1,
                        "total_pages": len(reader.pages),
                    },
                })
        log.info("Extracted %d valid text pages from PDF.", len(docs))
        return docs
    except Exception as exc:
        log.error("PDF extraction failed: %s", exc)
        raise RuntimeError(f"Failed to read PDF document: {exc}") from exc


def load_sec_filing(url: str, metadata: dict | None = None) -> list[dict]:
    """Fetch and parse an SEC EDGAR filing from its URL.
    
    Args:
        url: Full URL to the SEC EDGAR filing document (.htm or .txt).
        metadata: Filing metadata (ticker, form, filing_date, etc.).
        
    Returns:
        List of section documents ready for text splitting.
    """
    headers = {"User-Agent": settings.sec_user_agent}
    try:
        log.info("Fetching SEC filing from %s", url)
        r = requests.get(url, headers=headers, timeout=30)
        r.raise_for_status()
        content = r.content

        # Handle PDF filings
        if url.lower().endswith(".pdf") or content[:5] == b"%PDF-":
            return load_pdf(BytesIO(content), metadata)

        # Parse HTML / text filing
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(content, "html.parser")

        # Strip non-text tags
        for tag in soup(["script", "style", "table", "noscript", "meta"]):
            tag.decompose()

        text = soup.get_text(" ", strip=True)
        text = " ".join(text.split())

        if not text:
            log.warning("No readable text found in SEC filing at %s", url)
            return []

        # Break document into manageable sections (e.g. 15,000 chars each)
        chunk_len = 15000
        docs = []
        for i in range(0, len(text), chunk_len):
            section_text = text[i:i + chunk_len].strip()
            if section_text:
                docs.append({
                    "text": section_text,
                    "metadata": {
                        **(metadata or {}),
                        "section": i // chunk_len + 1,
                        "source_url": url,
                    },
                })

        log.info("Parsed SEC filing into %d sections from %s", len(docs), url)
        return docs
    except Exception as exc:
        log.error("Failed to load SEC filing from %s: %s", url, exc)
        raise RuntimeError(f"Failed to fetch SEC filing: {exc}") from exc


def load_global_document(source, metadata: dict | None = None) -> list[dict]:
    """Load any financial report or filing for a global company.
    
    Supports:
    - Uploaded PDF bytes/files
    - Local file paths
    - Remote URLs (SEC EDGAR, European ESMA, Indian NSE/BSE, Japanese EDINET, etc.)
    """
    meta = metadata or {}
    
    # If source is a file path or file-like object
    if hasattr(source, "read") or (isinstance(source, str) and not source.startswith("http")):
        return load_pdf(source, meta)
        
    # If source is a URL
    if isinstance(source, str) and source.startswith("http"):
        return load_sec_filing(source, meta)
        
    raise ValueError(f"Unsupported document source: {type(source)}")

