import pytest
from unittest.mock import AsyncMock
from app.agent.planner import PlannerError, ResearchPlan, ResearchPlanner
from app.schemas.research import ResearchDepth
from app.services.llm_service import LLMResponse, LLMUsage


@pytest.mark.asyncio
async def test_planner_creates_valid_plan():
    mock_llm = AsyncMock()
    mock_llm.generate_json.return_value = LLMResponse(
        content='{"objective": "Investigate CRISPR gene editing advances", "subquestions": ["What are recent clinical trials?"], "search_queries": ["CRISPR clinical trial results 2025"], "required_tools": ["tavily_search"], "expected_report_format": "Executive summary", "assumptions": ["Focus on human in-vivo"]}',
        parsed_json={
            "objective": "Investigate CRISPR gene editing advances",
            "subquestions": ["What are recent clinical trials?"],
            "search_queries": ["CRISPR clinical trial results 2025"],
            "required_tools": ["tavily_search"],
            "expected_report_format": "Executive summary",
            "assumptions": ["Focus on human in-vivo"],
        },
        provider="openai",
        model="gpt-4o-mini",
        latency_ms=120.0,
    )

    planner = ResearchPlanner(llm=mock_llm)
    plan = await planner.create_plan(
        query="What are the recent advances in CRISPR clinical trials?",
        depth=ResearchDepth.STANDARD,
        max_sources=5,
    )

    assert isinstance(plan, ResearchPlan)
    assert plan.objective == "Investigate CRISPR gene editing advances"
    assert len(plan.subquestions) == 1
    assert len(plan.search_queries) == 1
    assert plan.search_queries[0] == "CRISPR clinical trial results 2025"
    assert len(plan.steps) == 1
    assert plan.steps[0].search_query == "CRISPR clinical trial results 2025"
    assert plan.steps[0].status == "pending"


@pytest.mark.asyncio
async def test_planner_enforces_query_limits():
    mock_llm = AsyncMock()
    mock_llm.generate_json.return_value = LLMResponse(
        content="{}",
        parsed_json={
            "objective": "Study AI safety",
            "subquestions": ["Subquestion 1"],
            "search_queries": [
                "query 1", "query 2", "query 3", "query 4", "query 5", "query 6", "query 7",
            ],
        },
        provider="openai",
        model="gpt-4o-mini",
        latency_ms=100.0,
    )

    planner = ResearchPlanner(llm=mock_llm)
    plan = await planner.create_plan(
        query="AI safety benchmarks",
        depth=ResearchDepth.QUICK,  # Quick depth allows at most 2 queries
    )

    assert len(plan.search_queries) <= 2
    assert len(plan.steps) <= 2


@pytest.mark.asyncio
async def test_planner_recovery_after_initial_malformed_json():
    mock_llm = AsyncMock()
    # First attempt raises Exception, second attempt succeeds
    mock_llm.generate_json.side_effect = [
        Exception("Malformed JSON string"),
        LLMResponse(
            content="{}",
            parsed_json={
                "objective": "Recovered plan objective",
                "subquestions": ["Recovered subquestion"],
                "search_queries": ["recovered query"],
            },
            provider="openai",
            model="gpt-4o-mini",
            latency_ms=150.0,
        ),
    ]

    planner = ResearchPlanner(llm=mock_llm)
    plan = await planner.create_plan(query="Test query with recovery")
    assert plan.objective == "Recovered plan objective"
    assert plan.search_queries == ["recovered query"]


@pytest.mark.asyncio
async def test_planner_fails_when_all_attempts_exhausted():
    mock_llm = AsyncMock()
    mock_llm.generate_json.side_effect = Exception("Persistent LLM generation error")

    planner = ResearchPlanner(llm=mock_llm)
    with pytest.raises(PlannerError):
        await planner.create_plan(query="Query that fails")
