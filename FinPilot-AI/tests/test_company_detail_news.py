import ast
import inspect
from pathlib import Path

from backend.data.news_data import fetch_news


def test_company_detail_news_call_matches_fetch_news_signature():
    page_path = Path(__file__).resolve().parents[1] / "frontend" / "company_detail_page.py"
    page = ast.parse(page_path.read_text(encoding="utf-8"))
    calls = [
        node
        for node in ast.walk(page)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "fetch_news"
    ]

    assert len(calls) == 1
    supported_parameters = inspect.signature(fetch_news).parameters
    assert all(keyword.arg in supported_parameters for keyword in calls[0].keywords)


def test_fetch_news_returns_fields_used_by_finbert(monkeypatch):
    from backend.data.providers import yfinance_provider

    monkeypatch.setattr(yfinance_provider, "is_dns_online", lambda: False)

    articles = fetch_news("NVDA")

    assert articles
    assert {"title", "text", "published_at", "url", "source"} <= articles[0].keys()
