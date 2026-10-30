import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.schemas.research import (
    Citation,
    ConfidenceLevel,
    ConfidenceScore,
    EvidenceSource,
    ExecutionStatus,
    FindingItem,
    PlanStep,
    ResearchResponse,
)


@pytest.mark.asyncio
async def test_research_endpoint_missing_credentials_returns_503(monkeypatch):
    """Verify that when API credentials are missing, endpoint returns 503 instead of fabricating data."""
    from app.config import settings
    monkeypatch.setattr(settings, "gemini_api_key", None)
    monkeypatch.setattr(settings, "openai_api_key", None)
    monkeypatch.setattr(settings, "tavily_api_key", None)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "query": "What are the latest breakthroughs in solid state battery electrolytes?",
            "depth": "standard",
            "max_sources": 5,
        }
        response = await client.post("/api/v1/research", json=payload)
        assert response.status_code == 503
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "MISSING_CREDENTIALS"
        assert "X-Request-ID" in response.headers
        assert "X-Process-Time-Ms" in response.headers


@pytest.mark.asyncio
async def test_research_endpoint_success_with_mocked_workflow():
    """Verify complete research API response structure when workflow succeeds."""
    mock_response = ResearchResponse(
        query="What are the recent breakthroughs in perovskite solar cells?",
        status=ExecutionStatus.COMPLETED,
        executive_summary="Perovskite-silicon tandem solar cells achieved certified 34.6% power conversion efficiency.",
        findings=[
            FindingItem(
                heading="Record Tandem Efficiency",
                content="Certified test labs verified 34.6% efficiency using self-assembled monolayers [src-1].",
                citations=["src-1"],
            )
        ],
        plan=[
            PlanStep(
                step_id=1,
                description="Search recent perovskite tandem solar efficiency records 2025 2026",
                search_query="perovskite solar cell efficiency record 2025 2026",
                status="completed",
            )
        ],
        sources=[
            EvidenceSource(
                source_id="src-1",
                url="https://example.org/solar-records",
                title="Solar Energy Breakthroughs",
                domain="example.org",
                snippet="Lab tests confirm 34.6% tandem efficiency milestone.",
                raw_content="Full article content discussing perovskite tandem cells...",
                credibility_note="Peer-reviewed research institution release",
            )
        ],
        citations=[
            Citation(
                citation_id="cite-1",
                source_id="src-1",
                url="https://example.org/solar-records",
                source_title="Solar Energy Breakthroughs",
                cited_claim="34.6% efficiency verified in tandem tests",
            )
        ],
        confidence=ConfidenceScore(
            score=0.91,
            level=ConfidenceLevel.HIGH,
            explanation="Corroborated by independent certified test lab records.",
            limitations=["Long-term outdoor durability remains under testing."],
        ),
        assumptions=["Focus is on dual-junction tandem architectures."],
        limitations=["Long-term operational stability data is limited."],
        suggested_next_steps=["Examine encapsulation and moisture barrier technologies."],
        execution_time_seconds=3.42,
        metadata={"sources_evaluated": 5},
    )

    with patch("app.api.v1.research.orchestrator.execute_research", new=AsyncMock(return_value=mock_response)):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            payload = {
                "query": "What are the recent breakthroughs in perovskite solar cells?",
                "depth": "standard",
                "max_sources": 5,
            }
            response = await client.post("/api/v1/research", json=payload)
            assert response.status_code == 200
            data = response.json()
            assert data["query"] == payload["query"]
            assert data["status"] == "completed"
            assert len(data["findings"]) == 1
            assert len(data["sources"]) == 1
            assert len(data["citations"]) == 1
            assert data["confidence"]["level"] == "high"
            assert data["confidence"]["score"] == 0.91
            assert "X-Request-ID" in response.headers
            assert "X-Process-Time-Ms" in response.headers


@pytest.mark.asyncio
async def test_research_validation_empty_query():
    """Verify empty query returns structured 422 error without stack trace."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v1/research", json={"query": "   "})
        assert response.status_code == 422
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "VALIDATION_ERROR"
        details = data["error"]["details"]
        assert any("query" in d["field"] for d in details)


@pytest.mark.asyncio
async def test_research_validation_short_query():
    """Verify query shorter than 3 characters returns 422."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v1/research", json={"query": "ai"})
        assert response.status_code == 422
        data = response.json()
        assert data["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_research_validation_excessively_long_query():
    """Verify query exceeding 1000 characters returns 422."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v1/research", json={"query": "x" * 1001})
        assert response.status_code == 422
        data = response.json()
        assert data["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_research_validation_invalid_max_sources():
    """Verify max_sources out of bounds (1-20) returns 422."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Zero
        res_zero = await client.post(
            "/api/v1/research",
            json={"query": "Valid research topic", "max_sources": 0},
        )
        assert res_zero.status_code == 422

        # Greater than 20
        res_high = await client.post(
            "/api/v1/research",
            json={"query": "Valid research topic", "max_sources": 50},
        )
        assert res_high.status_code == 422
