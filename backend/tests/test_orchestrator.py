import pytest
from unittest.mock import AsyncMock, patch
from app.agent.orchestrator import OrchestratorError, ResearchOrchestrator
from app.agent.planner import ResearchPlan
from app.schemas.research import (
    ConfidenceLevel,
    ConfidenceScore,
    ExecutionStatus,
    FindingItem,
    PlanStep,
    ResearchDepth,
    ResearchRequest,
    ResearchResponse,
)
from app.tools.web_search import (
    SearchResultItem,
    SearchToolError,
    TavilyCredentialsError,
)
from app.tools.webpage_reader import ExtractedPage


@pytest.mark.asyncio
async def test_orchestrator_complete_success_flow():
    mock_planner = AsyncMock()
    mock_planner.create_plan.return_value = ResearchPlan(
        objective="Assess mRNA cancer vaccine pipeline",
        subquestions=["What are phase 3 clinical results?"],
        search_queries=["mRNA personalized cancer vaccine phase 3 results"],
        steps=[
            PlanStep(
                step_id=1,
                description="Search web for clinical results",
                search_query="mRNA personalized cancer vaccine phase 3 results",
                status="pending",
            )
        ],
    )

    from unittest.mock import MagicMock
    mock_search = AsyncMock()
    mock_search.search.return_value = MagicMock(
        results=[
            SearchResultItem(
                title="Melanoma Phase 3 Trial Data",
                url="https://example.org/melanoma-trial",
                snippet="Adjuvant mRNA-4157 combined with pembrolizumab showed 49% recurrence reduction.",
                domain="example.org",
            )
        ]
    )

    mock_reader = AsyncMock()
    mock_reader.fetch_multiple_pages.return_value = [
        ExtractedPage(
            url="https://example.org/melanoma-trial",
            final_url="https://example.org/melanoma-trial",
            title="Melanoma Phase 3 Trial Data",
            content="Detailed results confirm durable recurrence-free survival benefits over three years.",
            content_length=95,
            http_status=200,
            content_type="text/html",
        )
    ]

    mock_synthesizer = AsyncMock()
    mock_synthesizer.synthesize.return_value = ResearchResponse(
        query="mRNA cancer vaccine progress",
        status=ExecutionStatus.COMPLETED,
        executive_summary="Personalized mRNA vaccines demonstrated significant recurrence-free survival improvements.",
        findings=[
            FindingItem(
                heading="Three-Year Recurrence Benefit",
                content="Combination therapy reduced risk of recurrence by 49% [src-1].",
                citations=["src-1"],
            )
        ],
        plan=[],
        sources=[],
        citations=[],
        confidence=ConfidenceScore(
            score=0.92,
            level=ConfidenceLevel.HIGH,
            explanation="Supported by peer-reviewed multi-center clinical trials.",
        ),
    )

    orchestrator = ResearchOrchestrator(
        plan_generator=mock_planner,
        search_engine=mock_search,
        page_reader=mock_reader,
        answer_synth=mock_synthesizer,
    )

    req = ResearchRequest(query="mRNA cancer vaccine progress", depth=ResearchDepth.STANDARD, max_sources=5)
    resp = await orchestrator.execute_research(req)

    assert resp.status == ExecutionStatus.COMPLETED
    assert "Personalized mRNA vaccines" in resp.executive_summary
    assert len(resp.findings) == 1
    assert resp.execution_time_seconds is not None
    assert resp.execution_time_seconds >= 0.0
    assert len(resp.plan) == 1
    assert resp.plan[0].status == "completed"


@pytest.mark.asyncio
async def test_orchestrator_partial_tool_failure_continues():
    mock_planner = AsyncMock()
    mock_planner.create_plan.return_value = ResearchPlan(
        objective="Quantum computing comparison",
        subquestions=["Superconducting vs Ion trap"],
        search_queries=["superconducting qubits 2026", "ion trap fidelity 2026"],
        steps=[
            PlanStep(step_id=1, description="Search 1", search_query="superconducting qubits 2026"),
            PlanStep(step_id=2, description="Search 2", search_query="ion trap fidelity 2026"),
        ],
    )

    from unittest.mock import MagicMock
    mock_search = AsyncMock()
    # First search succeeds, second search fails with transient SearchToolError
    mock_search.search.side_effect = [
        MagicMock(results=[
            SearchResultItem(
                title="Superconducting Progress",
                url="https://example.org/superconducting",
                snippet="Coherence times doubled in 3D cavity architecture.",
                domain="example.org",
            )
        ]),
        SearchToolError("Search provider connection timeout"),
    ]

    mock_reader = AsyncMock()
    mock_reader.fetch_multiple_pages.return_value = []

    mock_synthesizer = AsyncMock()
    mock_synthesizer.synthesize.return_value = ResearchResponse(
        query="Quantum computing comparison",
        status=ExecutionStatus.COMPLETED,
        executive_summary="Superconducting qubit coherence times improved significantly.",
        findings=[],
        plan=[],
        sources=[],
        citations=[],
        confidence=ConfidenceScore(
            score=0.70,
            level=ConfidenceLevel.MEDIUM,
            explanation="Based on partial search results.",
        ),
    )

    orchestrator = ResearchOrchestrator(
        plan_generator=mock_planner,
        search_engine=mock_search,
        page_reader=mock_reader,
        answer_synth=mock_synthesizer,
    )

    req = ResearchRequest(query="Quantum computing comparison", depth=ResearchDepth.STANDARD)
    resp = await orchestrator.execute_research(req)

    assert resp.status == ExecutionStatus.COMPLETED
    assert resp.metadata.get("partial_result") is True
    assert any("Partial search failure" in lim for lim in resp.limitations)
    assert resp.plan[0].status == "completed"
    assert resp.plan[1].status == "failed"


@pytest.mark.asyncio
async def test_orchestrator_all_searches_fail_raises_error():
    mock_planner = AsyncMock()
    mock_planner.create_plan.return_value = ResearchPlan(
        objective="Failed query",
        subquestions=["Failed question"],
        search_queries=["query 1"],
        steps=[PlanStep(step_id=1, description="Step 1", search_query="query 1")],
    )

    mock_search = AsyncMock()
    mock_search.search.side_effect = SearchToolError("All connections refused")

    orchestrator = ResearchOrchestrator(
        plan_generator=mock_planner,
        search_engine=mock_search,
    )

    req = ResearchRequest(query="Failed query")
    with pytest.raises(OrchestratorError) as exc:
        await orchestrator.execute_research(req)
    assert exc.value.code == "SEARCH_FAILED"


@pytest.mark.asyncio
async def test_orchestrator_missing_tavily_credentials_raises_clean_error():
    mock_planner = AsyncMock()
    mock_planner.create_plan.return_value = ResearchPlan(
        objective="Query needing key",
        subquestions=["Question"],
        search_queries=["query needing key"],
        steps=[PlanStep(step_id=1, description="Step 1", search_query="query needing key")],
    )

    mock_search = AsyncMock()
    mock_search.search.side_effect = TavilyCredentialsError("Tavily API key is unconfigured.")

    orchestrator = ResearchOrchestrator(
        plan_generator=mock_planner,
        search_engine=mock_search,
    )

    req = ResearchRequest(query="Query needing key")
    with pytest.raises(OrchestratorError) as exc:
        await orchestrator.execute_research(req)
    assert exc.value.code == "MISSING_CREDENTIALS"
