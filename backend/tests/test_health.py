import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.config import settings


@pytest.mark.asyncio
async def test_root_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "ResearchPilot API" in data["message"]
        assert data["health_url"] == "/health"
        assert "version" in data


@pytest.mark.asyncio
async def test_root_health_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["app"] == "ResearchPilot API"
        assert "services" in data
        assert "llm_configured" in data["services"]
        assert "tavily_configured" in data["services"]
        assert data["services"]["extractor_operational"] is True


@pytest.mark.asyncio
async def test_api_v1_health():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_health_llm_missing_credentials(monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", None)
    monkeypatch.setattr(settings, "llm_provider", "openai")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health/llm")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "missing_credentials"
        assert data["configured"] is False
        assert "OPENAI_API_KEY" in data["message"]


@pytest.mark.asyncio
async def test_health_llm_configured(monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", "sk-mock-key-for-testing-only")
    monkeypatch.setattr(settings, "llm_provider", "openai")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health/llm")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "configured"
        assert data["configured"] is True
        assert "openai" in data["message"].lower()


@pytest.mark.asyncio
async def test_health_tools_missing_credentials(monkeypatch):
    monkeypatch.setattr(settings, "tavily_api_key", None)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health/tools")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "partially_configured"
        tavily_tool = next(t for t in data["tools"] if t["name"] == "tavily_search")
        assert tavily_tool["status"] == "missing_credentials"
        assert tavily_tool["configured"] is False


@pytest.mark.asyncio
async def test_health_tools_configured(monkeypatch):
    monkeypatch.setattr(settings, "tavily_api_key", "tvly-mock-key-for-testing-only")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health/tools")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "operational"
        tavily_tool = next(t for t in data["tools"] if t["name"] == "tavily_search")
        assert tavily_tool["status"] == "configured"
        assert tavily_tool["configured"] is True

        extractor_tool = next(t for t in data["tools"] if t["name"] == "web_extractor")
        assert extractor_tool["status"] == "verified"
        assert extractor_tool["configured"] is True
        assert extractor_tool["verified"] is True
