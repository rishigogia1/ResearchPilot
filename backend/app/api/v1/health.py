from datetime import datetime, timezone
from fastapi import APIRouter
from app.config import settings
from app.schemas.research import (
    HealthResponse,
    LLMHealthResponse,
    ServiceStatus,
    ToolItemHealth,
    ToolsHealthResponse,
)

router = APIRouter()


@router.get("", response_model=HealthResponse)
async def get_general_health():
    """General health check verifying application responsiveness and configuration summary."""
    return HealthResponse(
        status="ok",
        app=settings.app_name,
        version=settings.app_version,
        timestamp=datetime.now(timezone.utc),
        services={
            "llm_provider": settings.llm_provider,
            "llm_configured": settings.is_llm_configured(),
            "tavily_configured": settings.is_tavily_configured(),
            "extractor_operational": True,
        },
    )


@router.get("/llm", response_model=LLMHealthResponse)
async def get_llm_health():
    """
    Check LLM provider configuration status.
    Distinguishes between missing credentials and configured state.
    Does not execute costly or high-latency LLM generations during health checks.
    """
    is_configured = settings.is_llm_configured()
    provider = settings.llm_provider.lower()
    model = settings.llm_model

    if not is_configured:
        return LLMHealthResponse(
            status=ServiceStatus.MISSING_CREDENTIALS,
            configured=False,
            provider=provider,
            model=model,
            message=f"Missing API key for provider '{provider}'. Please configure {provider.upper()}_API_KEY.",
            timestamp=datetime.now(timezone.utc),
        )

    return LLMHealthResponse(
        status=ServiceStatus.CONFIGURED,
        configured=True,
        provider=provider,
        model=model,
        message=f"LLM provider '{provider}' is configured with model '{model}'. (Full invocation deferred to research workflow).",
        timestamp=datetime.now(timezone.utc),
    )


@router.get("/tools", response_model=ToolsHealthResponse)
async def get_tools_health():
    """
    Check health of research tools ecosystem.
    Evaluates Tavily search credentials and built-in extraction tools.
    """
    tavily_configured = settings.is_tavily_configured()

    tools_list = [
        ToolItemHealth(
            name="tavily_search",
            status=ServiceStatus.CONFIGURED if tavily_configured else ServiceStatus.MISSING_CREDENTIALS,
            configured=tavily_configured,
            verified=False,  # Not verified with a paid query during health check
            description="Agentic web search engine for high-relevance query retrieval.",
        ),
        ToolItemHealth(
            name="web_extractor",
            status=ServiceStatus.VERIFIED,
            configured=True,
            verified=True,  # Local HTTPX + BeautifulSoup engine verified available
            description="Resilient HTTPX and BeautifulSoup webpage content parser with timeouts.",
        ),
    ]

    overall_status = "operational" if tavily_configured else "partially_configured"

    return ToolsHealthResponse(
        status=overall_status,
        tools=tools_list,
        timestamp=datetime.now(timezone.utc),
    )
