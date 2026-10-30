import pytest
from unittest.mock import AsyncMock, patch
from tavily import InvalidAPIKeyError
from app.tools.web_search import (
    SearchResultItem,
    TavilyAuthError,
    TavilyCredentialsError,
    TavilySearchTool,
    normalize_url,
)


def test_normalize_url():
    # Strips utm parameters and tracking tokens
    url_with_tracking = "https://example.com/article/?utm_source=twitter&utm_medium=social&ref=123#heading"
    normalized = normalize_url(url_with_tracking)
    assert normalized == "https://example.com/article"

    # Handles trailing slash consistently
    assert normalize_url("https://example.com/path/") == "https://example.com/path"

    # Rejects invalid schemes
    assert normalize_url("ftp://example.com/file") is None
    assert normalize_url("javascript:alert(1)") is None
    assert normalize_url("") is None


@pytest.mark.asyncio
async def test_tavily_search_missing_credentials(monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "tavily_api_key", None)

    tool = TavilySearchTool()
    with pytest.raises(TavilyCredentialsError):
        await tool.search("quantum computing")


@pytest.mark.asyncio
async def test_tavily_search_empty_query():
    tool = TavilySearchTool(api_key="tvly-mock-key")
    res = await tool.search("   ")
    assert res.total_results == 0
    assert len(res.results) == 0


@pytest.mark.asyncio
async def test_tavily_search_deduplication():
    tool = TavilySearchTool(api_key="tvly-mock-key")

    mock_raw_response = {
        "results": [
            {
                "title": "Quantum Supremacy Milestone",
                "url": "https://example.org/quantum-1?utm_source=newsletter",
                "content": "Researchers demonstrated quantum supremacy with neutral atom qubits.",
                "score": 0.95,
                "published_date": "2025-11-12",
            },
            {
                "title": "Quantum Supremacy Milestone (Duplicate)",
                "url": "https://example.org/quantum-1",  # Same canonical URL
                "content": "Duplicate content snippet.",
                "score": 0.90,
            },
            {
                "title": "Ion Trap Advances",
                "url": "https://example.org/quantum-2",
                "content": "Trapped ion fidelities reached four nines threshold.",
                "score": 0.88,
            },
        ]
    }

    with patch("app.tools.web_search.AsyncTavilyClient") as mock_client_cls:
        mock_instance = AsyncMock()
        mock_instance.search.return_value = mock_raw_response
        mock_client_cls.return_value = mock_instance

        resp = await tool.search("quantum computing breakthroughs", max_results=5)
        # Verify deduplication reduced 3 raw results to 2 unique URLs
        assert resp.total_results == 2
        assert len(resp.results) == 2
        assert resp.results[0].url == "https://example.org/quantum-1"
        assert resp.results[1].url == "https://example.org/quantum-2"
        assert resp.results[0].score == 0.95
        assert resp.results[0].published_date == "2025-11-12"


@pytest.mark.asyncio
async def test_tavily_search_auth_failure():
    tool = TavilySearchTool(api_key="tvly-invalid-key")

    with patch("app.tools.web_search.AsyncTavilyClient") as mock_client_cls:
        mock_instance = AsyncMock()
        mock_instance.search.side_effect = InvalidAPIKeyError("Invalid API key")
        mock_client_cls.return_value = mock_instance

        with pytest.raises(TavilyAuthError):
            await tool.search("solid state battery")
