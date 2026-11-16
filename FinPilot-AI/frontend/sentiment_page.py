"""FinBERT Financial Sentiment Analysis page."""
import streamlit as st
import plotly.graph_objects as go
import pandas as pd


def render_sentiment():
    """Render FinBERT sentiment breakdown, distribution chart, and classified headlines."""
    st.markdown("## 📰 FinBERT Financial Sentiment Analysis")
    st.caption("Powered by `ProsusAI/finbert` — a specialized transformer trained on financial news corpora.")

    analysis = st.session_state.get("analysis")
    if not analysis:
        st.info("💡 Open **Explore**, select a company, and run its quantitative analysis first.")
        return

    sentiment = analysis.get("sentiment", {})
    sentiment_df = analysis.get("sentiment_df")
    ticker = analysis["ticker"]

    if not sentiment.get("available") or sentiment_df is None or sentiment_df.empty:
        st.warning(
            f"⚠️ **Sentiment Analysis Unavailable for {ticker}:**\n\n"
            f"{sentiment.get('message', 'No news retrieved.')}\n\n"
            "To activate real-time financial sentiment analysis:\n"
            "1. Obtain a free API key from [Finnhub.io](https://finnhub.io) or [NewsAPI.org](https://newsapi.org)\n"
            "2. Add `FINNHUB_API_KEY=your_key` to your `.env` file\n"
            "3. Re-run analysis from the Dashboard."
        )
        return

    # Overall Metrics Banner
    st.markdown(f"### Sentiment Overview for {analysis.get('company_name', ticker)}")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric(
            label="Overall Sentiment Score",
            value=f"{sentiment.get('score', 0.0):+.3f}",
            delta=sentiment.get("overall_label", "Neutral"),
            delta_color="normal" if sentiment.get("overall_label") == "Positive" else "inverse",
        )
    with c2:
        st.metric(
            label="Positive News",
            value=f"{sentiment.get('positive_pct', 0.0):.1f}%",
        )
    with c3:
        st.metric(
            label="Negative News",
            value=f"{sentiment.get('negative_pct', 0.0):.1f}%",
        )
    with c4:
        st.metric(
            label="Neutral News",
            value=f"{sentiment.get('neutral_pct', 0.0):.1f}%",
        )

    # Donut Chart & Score Distribution
    st.markdown("---")
    chart_col, detail_col = st.columns([1, 1])

    with chart_col:
        st.markdown("#### Sentiment Distribution")
        fig = go.Figure(data=[go.Pie(
            labels=["Positive", "Neutral", "Negative"],
            values=[
                sentiment.get("positive_pct", 0.0),
                sentiment.get("neutral_pct", 0.0),
                sentiment.get("negative_pct", 0.0),
            ],
            hole=0.55,
            marker=dict(colors=["#10b981", "#64748b", "#f43f5e"]),
            textinfo="label+percent",
            hoverinfo="label+value",
        )])
        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            height=320,
            margin=dict(l=0, r=0, t=10, b=0),
            showlegend=False,
        )
        st.plotly_chart(fig, use_container_width=True)

    with detail_col:
        st.markdown("#### FinBERT Technical Details")
        st.write(f"• **Analyzed Articles:** `{sentiment.get('count', len(sentiment_df))}`")
        st.write("• **Base Architecture:** `BERT-base-uncased` with fine-tuned financial classification head")
        st.write("• **Sentiment Score Formula:** `Mean(P(Positive) - P(Negative))` across all articles")
        st.write("• **Input Scope:** Headlines and article lead summaries within the last 21 days")
        st.caption("🔒 FinBERT sentiment features are forward-filled for the latest observation without introducing future lookahead.")

    st.markdown("---")

    # Filter & Articles Table
    st.markdown(f"### Classified Financial News Items ({len(sentiment_df)} articles)")
    filter_choice = st.radio(
        "Filter by Sentiment Classification:",
        options=["All", "Positive", "Negative", "Neutral"],
        horizontal=True,
    )

    filtered_df = sentiment_df
    if filter_choice != "All":
        filtered_df = sentiment_df[sentiment_df["label"] == filter_choice.lower()]

    for _, row in filtered_df.iterrows():
        lbl = str(row.get("label", "neutral")).upper()
        badge_style = "badge-positive" if lbl == "POSITIVE" else ("badge-negative" if lbl == "NEGATIVE" else "badge-neutral")
        pub = str(row.get("published_at", "Recent"))
        source = str(row.get("source", "Financial News"))

        st.markdown(f"""
            <div class="finpilot-card" style="margin-bottom: 12px; padding: 14px 18px;">
                <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                    <span class="{badge_style}" style="margin-bottom: 6px;">{lbl}</span>
                    <span style="font-size: 0.8rem; color: #64748b;">
                        <b>{row.get('identified_company', ticker)}</b> • {pub} • {source}
                    </span>
                </div>
                <h4 style="margin: 6px 0 4px 0; font-size: 1.05rem; color: #f1f5f9;">
                    {row.get('title', 'Untitled')}
                </h4>
                <p style="margin: 0 0 8px 0; font-size: 0.9rem; color: #94a3b8;">
                    {row.get('text', '')[:300]}{'...' if len(str(row.get('text', ''))) > 300 else ''}
                </p>
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span style="font-size: 0.8rem; color: #64748b;">
                        P(+): <b>{row.get('positive', 0.0):.2f}</b> | 
                        P(-): <b>{row.get('negative', 0.0):.2f}</b> | 
                        P(0): <b>{row.get('neutral', 0.0):.2f}</b>
                    </span>
                    {f'<a href="{row.get("url")}" target="_blank" style="font-size: 0.85rem; color: #38bdf8; text-decoration: none;">Read Original ↗</a>' if row.get("url") else ''}
                </div>
            </div>
        """, unsafe_allow_html=True)
