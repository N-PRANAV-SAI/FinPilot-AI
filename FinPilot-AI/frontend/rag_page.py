"""RAG Financial Research Page for FinPilot AI supporting global filings and reports."""
import streamlit as st
from backend.rag.retriever import FinancialRetriever
from backend.rag.document_loader import load_pdf
from backend.data.filings_data import discover_company_documents
from backend.llm.explanation_generator import generate_explanation


def render_rag():
    """Render RAG document ingestion, semantic search, and evidence-grounded AI answers for global companies."""
    st.markdown("## 🔍 Global RAG Financial Document Research & Evidence")
    st.caption("Retrieval-Augmented Generation using Sentence Transformers, ChromaDB, Global Regulatory Disclosures, and Uploaded Company Reports.")

    analysis = st.session_state.get("analysis")
    ticker = st.session_state.get("ticker", "NVDA").upper()
    comp_name = ticker
    country = "Global"
    exchange = "Exchange"

    if analysis:
        ticker = analysis.get("ticker", ticker)
        comp_name = analysis.get("company_name", ticker)
        country = analysis.get("country", "Global")
        exchange = analysis.get("exchange", "Exchange")

    flag = analysis.get("flag", "🌐") if analysis else "🌐"

    # Document Ingestion Section
    st.markdown(f"### 1. Ingest Financial Documents for {flag} {comp_name} ({ticker})")
    tab_filings, tab_pdf, tab_status = st.tabs([
        f"🏛️ {country} Regulatory Disclosures",
        "📄 Upload Company Financial PDF (Global)",
        "💾 Vector Store Memory Stats",
    ])

    with tab_filings:
        st.write(f"Discover and index official regulatory filings, annual reports, or disclosures for **{comp_name}** ({exchange}, {country}):")
        col_btn, _ = st.columns([3, 5])
        with col_btn:
            discover_clicked = st.button("🔎 Fetch Available Regulatory Disclosures", use_container_width=True)

        if discover_clicked or "discovered_filings" not in st.session_state:
            with st.spinner(f"Querying regulatory document endpoints for {ticker} ({country})..."):
                try:
                    filings = discover_company_documents(
                        ticker=ticker,
                        company_name=comp_name,
                        country=country,
                        exchange=exchange,
                        limit=8,
                    )
                    st.session_state["discovered_filings"] = filings
                except Exception as exc:
                    st.error(f"Failed to fetch filings: {exc}")

        filings = st.session_state.get("discovered_filings", [])
        if filings:
            st.markdown(f"##### Discovered Regulatory Documents ({country}):")
            for idx, filing in enumerate(filings):
                f_col1, f_col2, f_col3 = st.columns([4, 2, 2])
                doc_title = filing.get("title") or filing.get("document_type", "Filing")
                f_col1.write(f"📄 **{doc_title}**")
                f_col2.write(f"Date: `{filing.get('date', 'N/A')}`")
                with f_col3:
                    f_url = filing.get("url", "")
                    if f_url and "sec.gov" in f_url:
                        if st.button(f"📥 Index Filing #{idx+1}", key=f"idx_filing_{idx}"):
                            with st.spinner(f"Ingesting and chunking {filing.get('form', 'document')}..."):
                                try:
                                    ret = FinancialRetriever()
                                    n_chunks = ret.ingest_sec_filing(
                                        url=f_url,
                                        ticker=ticker,
                                        metadata={
                                            "document_title": doc_title,
                                            "form": filing.get("form"),
                                            "filing_date": filing.get("date"),
                                            "source_url": f_url,
                                            "document_type": filing.get("document_type", "regulatory_filing"),
                                            "country": country,
                                            "exchange": exchange,
                                            "ticker": ticker,
                                        },
                                    )
                                    st.success(f"Indexed {n_chunks} chunks into ChromaDB vector store!")
                                except Exception as exc:
                                    st.error(f"Failed to index filing: {exc}")
                    else:
                        st.markdown(f"<a href='{f_url}' target='_blank' style='color:#38bdf8; font-size:0.85rem; text-decoration:none;'>Open Portal ↗</a>", unsafe_allow_html=True)
                st.markdown("<hr style='margin: 4px 0; border-color: #1e293b;'>", unsafe_allow_html=True)
        else:
            st.info(f"No direct online API filing links returned for {ticker}. You can upload any official annual report PDF in the next tab!")

    with tab_pdf:
        st.write(f"Upload any annual report, quarterly disclosure, earnings call transcript, or investor presentation PDF for **{comp_name}**:")
        uploaded_file = st.file_uploader(f"Choose a PDF report for {ticker}", type=["pdf"])
        if uploaded_file is not None:
            doc_title = st.text_input("Document Title", value=uploaded_file.name)
            if st.button("⚡ Index Uploaded PDF into Vector Store", type="primary"):
                with st.spinner(f"Extracting text pages, computing embeddings, and indexing into ChromaDB for {ticker}..."):
                    try:
                        docs = load_pdf(
                            uploaded_file,
                            metadata={
                                "document_title": doc_title,
                                "document_type": "company_pdf_report",
                                "country": country,
                                "exchange": exchange,
                                "ticker": ticker,
                                "source_url": f"uploaded://{uploaded_file.name}",
                            },
                        )
                        retriever = FinancialRetriever()
                        count = retriever.ingest(
                            docs=docs,
                            ticker=ticker,
                            document_metadata={
                                "document_title": doc_title,
                                "document_type": "company_pdf_report",
                                "country": country,
                                "exchange": exchange,
                            },
                        )
                        st.success(f"Indexed {count} evidence chunks from '{doc_title}' for {ticker} ({comp_name})!")
                    except Exception as exc:
                        st.error(f"PDF indexing failed: {exc}")

    with tab_status:
        try:
            stats = FinancialRetriever().get_stats()
            st.metric("Total Indexed Chunks in ChromaDB", stats.get("total_chunks", 0))
            st.caption("Embeddings: `sentence-transformers/all-MiniLM-L6-v2` | Storage: Persistent ChromaDB collection.")
        except Exception as exc:
            st.warning(f"Vector store status unavailable: {exc}")

    st.markdown("---")

    # -------------------------------------------------------------
    # Semantic Query & Evidence Retrieval Section
    # -------------------------------------------------------------
    st.markdown("### 2. Query Financial Evidence & Grounded AI Synthesis")
    default_q = f"What are {comp_name}'s primary business and operational risks in {country}?"
    user_query = st.text_input(
        "Enter your financial research question:",
        value=default_q,
        placeholder=f"e.g. What were {comp_name}'s major business risks and revenue drivers in the latest report?",
    )

    k_slider = st.slider("Evidence passages to retrieve (k)", min_value=1, max_value=8, value=4)

    if st.button("🔎 Retrieve Evidence & Synthesize", type="primary"):
        if not user_query.strip():
            st.error("Please enter a research question.")
        else:
            with st.spinner(f"Searching ChromaDB vector store for '{user_query}'..."):
                retriever = FinancialRetriever()
                evidence = retriever.retrieve(user_query, ticker, k=k_slider)

                if not evidence:
                    st.warning(
                        f"No indexed evidence found for {ticker} ({comp_name}). "
                        "Please index a regulatory disclosure or upload a financial PDF above first."
                    )
                else:
                    st.markdown(f"#### 📑 Retrieved Evidence Passages ({len(evidence)} chunks)")
                    for i, passage in enumerate(evidence):
                        meta = passage.get("metadata", {})
                        title = meta.get("document_title", "Document")
                        page = meta.get("page", meta.get("section", "N/A"))
                        date = meta.get("filing_date", "N/A")
                        url = meta.get("source_url", "")
                        score = passage.get("relevance_score", 0.0)

                        st.markdown(f"""
                            <div class="citation-box">
                                <div style="display: flex; justify-content: space-between; font-size: 0.85rem; color: #38bdf8; font-weight: 600; margin-bottom: 6px;">
                                    <span>#{i+1} • {title} (Page/Sec: {page})</span>
                                    <span>Relevance: {score:.1%} • Date: {date}</span>
                                </div>
                                <div style="color: #e2e8f0; font-size: 0.92rem; line-height: 1.5;">
                                    "{passage.get('text', '')}"
                                </div>
                                {f'<div style="margin-top: 6px;"><a href="{url}" target="_blank" style="color: #94a3b8; font-size: 0.8rem;">View Source URL ↗</a></div>' if url and not url.startswith('uploaded://') else ''}
                            </div>
                        """, unsafe_allow_html=True)

                    # Generate LLM answer grounded in the retrieved evidence
                    st.markdown("#### 🤖 Grounded AI Synthesis")
                    with st.spinner("Generating evidence-grounded answer with Gemini..."):
                        pred = analysis.get("prediction", {}) if analysis else {}
                        sent = analysis.get("sentiment", {}) if analysis else {}
                        shap_v = analysis.get("shap_info", {}) if analysis else {}
                        funds = analysis.get("fundamentals", {}) if analysis else {}

                        answer = generate_explanation(
                            ticker=ticker,
                            prediction=pred,
                            sentiment=sent,
                            evidence=evidence,
                            shap_info=shap_v,
                            fundamentals=funds,
                            user_question=user_query,
                        )
                        st.markdown(answer)
