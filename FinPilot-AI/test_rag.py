import sys
import io
from pathlib import Path

workspace = Path(r"C:\Users\Pranav\Downloads\FinPilot-AI\FinPilot-AI")
if str(workspace) not in sys.path:
    sys.path.insert(0, str(workspace))

from backend.rag.retriever import FinancialRetriever
from backend.rag.document_loader import load_pdf

def test_rag_pipeline():
    print("=====================================================")
    print("TESTING RAG: PDF INGESTION & SEMANTIC RETRIEVAL")
    print("=====================================================")

    # Create a small valid test PDF using pypdf / reportlab or basic PDF stream
    # A minimal valid PDF structure with real financial text:
    pdf_content = b"""%PDF-1.4
1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj
2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj
3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj
4 0 obj << /Length 340 >> stream
BT
/F1 12 Tf
50 700 Td
(Apple Inc. Q4 Fiscal 2024 Financial Performance Report.) Tj
0 -20 Td
(Total net revenue reached $94.9 billion, an increase of 6% year-over-year.) Tj
0 -20 Td
(iPhone revenue was $46.2 billion driven by strong iPhone 16 demand.) Tj
0 -20 Td
(Services revenue set an all-time record of $24.97 billion with 74.0% gross margin.) Tj
0 -20 Td
(Key risk factors include geopolitical supply chain disruptions and foreign currency volatility.) Tj
ET
endstream
endobj
5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj
xref
0 6
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000226 00000 n 
0000000618 00000 n 
trailer << /Size 6 /Root 1 0 R >>
startxref
697
%%EOF"""

    pdf_stream = io.BytesIO(pdf_content)
    meta = {
        "ticker": "AAPL",
        "document_title": "Apple Q4 2024 Financial Results",
        "filing_date": "2024-10-31",
        "form": "10-Q/Earnings"
    }

    print("\n1. Extracting text pages from PDF...")
    pages = load_pdf(pdf_stream, meta)
    print(f"   -> Extracted {len(pages)} pages.")
    for p in pages:
        print(f"   -> Page {p['metadata']['page']}: {p['text'][:120]}...")

    print("\n2. Ingesting pages into ChromaDB Vector Store via SentenceTransformers...")
    retriever = FinancialRetriever()
    chunk_count = retriever.ingest(pages, "AAPL", meta)
    print(f"   -> Ingested {chunk_count} chunks into ChromaDB.")

    print("\n3. Testing Semantic Retrieval Query...")
    question = "What was the Services segment revenue and gross margin?"
    evidence = retriever.retrieve(question, "AAPL", k=3)
    print(f"   -> Retrieved {len(evidence)} passages for question: '{question}'")
    for i, ev in enumerate(evidence, 1):
        m = ev["metadata"]
        print(f"   [{i}] Score: {ev.get('relevance_score', 0):.4f} (Distance: {ev.get('distance', 0):.4f})")
        print(f"       Title: {m.get('document_title')} | Date: {m.get('filing_date')} | Page: {m.get('page')}")
        print(f"       Snippet: \"{ev['text']}\"")

    assert len(evidence) > 0, "No evidence retrieved!"
    assert any("Services" in ev["text"] for ev in evidence), "Missing Services revenue in retrieved evidence"
    print("\n=====================================================")
    print("RAG PIPELINE VERIFICATION PASSED SUCCESSFULLY!")
    print("=====================================================")

if __name__ == "__main__":
    test_rag_pipeline()
