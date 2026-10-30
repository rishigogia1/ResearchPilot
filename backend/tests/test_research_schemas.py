import pytest
from pydantic import ValidationError
from app.schemas.research import (
    Citation,
    ConfidenceLevel,
    ConfidenceScore,
    EvidenceSource,
    ExecutionStatus,
    FindingItem,
    PlanStep,
    ResearchDepth,
    ResearchRequest,
    ResearchResponse,
)


def test_valid_research_request():
    req = ResearchRequest(query="What are the recent breakthroughs in mRNA vaccine technology?")
    assert req.query == "What are the recent breakthroughs in mRNA vaccine technology?"
    assert req.depth == ResearchDepth.STANDARD
    assert req.max_sources == 5


def test_research_request_custom_params():
    req = ResearchRequest(
        query="Explain quantum error correction methods",
        depth=ResearchDepth.DEEP,
        max_sources=15,
    )
    assert req.depth == ResearchDepth.DEEP
    assert req.max_sources == 15


def test_research_request_query_strip_whitespace():
    req = ResearchRequest(query="   Investigating solid state batteries   ")
    assert req.query == "Investigating solid state batteries"


def test_research_request_empty_query():
    with pytest.raises(ValidationError) as exc:
        ResearchRequest(query="")
    assert "query" in str(exc.value)


def test_research_request_whitespace_only():
    with pytest.raises(ValidationError) as exc:
        ResearchRequest(query="     ")
    assert "query" in str(exc.value)


def test_research_request_too_short():
    with pytest.raises(ValidationError) as exc:
        ResearchRequest(query="ab")
    assert "query" in str(exc.value)


def test_research_request_excessively_long():
    long_query = "x" * 1001
    with pytest.raises(ValidationError) as exc:
        ResearchRequest(query=long_query)
    assert "query" in str(exc.value)


def test_research_request_invalid_source_limits():
    # 0 sources
    with pytest.raises(ValidationError):
        ResearchRequest(query="Valid query here", max_sources=0)

    # Negative sources
    with pytest.raises(ValidationError):
        ResearchRequest(query="Valid query here", max_sources=-3)

    # Over limit (> 20)
    with pytest.raises(ValidationError):
        ResearchRequest(query="Valid query here", max_sources=25)


def test_full_research_response_schema():
    response = ResearchResponse(
        query="What are the latest developments in fusion energy?",
        status=ExecutionStatus.COMPLETED,
        executive_summary="Recent experiments at NIF and ITER have demonstrated net energy gain...",
        findings=[
            FindingItem(
                heading="Net Energy Gain Milestone",
                content="Laser fusion at NIF yielded a target gain factor exceeding 1.5 in repeated shots.",
                citations=["cite-1"],
            )
        ],
        plan=[
            PlanStep(
                step_id=1,
                description="Search for peer-reviewed fusion gain demonstrations 2024-2026",
                search_query="nuclear fusion net energy gain experiment results 2025 2026",
                status="completed",
            )
        ],
        sources=[
            EvidenceSource(
                source_id="src-1",
                url="https://example.org/fusion-breakthrough",
                title="Fusion Energy Progress",
                domain="example.org",
                snippet="Researchers confirmed repeated ignition conditions with high laser power.",
                raw_content="Full parsed text extract...",
                credibility_note="Academic peer-reviewed publication",
            )
        ],
        citations=[
            Citation(
                citation_id="cite-1",
                source_id="src-1",
                url="https://example.org/fusion-breakthrough",
                source_title="Fusion Energy Progress",
                cited_claim="Target gain factor exceeding 1.5 in repeated shots.",
            )
        ],
        confidence=ConfidenceScore(
            score=0.92,
            level=ConfidenceLevel.HIGH,
            explanation="Multiple high-credibility experimental sources corroborate these numbers.",
            limitations=["Commercial scale electrical conversion remains untested."],
        ),
        assumptions=["Data refers to thermal laser energy, not wall-plug electrical efficiency."],
        limitations=["Commercial viability timelines remain uncertain."],
        suggested_next_steps=["Investigate magnetic confinement tokamak comparisons."],
        execution_time_seconds=4.82,
        metadata={"worker_count": 4},
    )

    dumped = response.model_dump()
    assert dumped["status"] == "completed"
    assert dumped["confidence"]["level"] == "high"
    assert len(dumped["findings"]) == 1
    assert len(dumped["sources"]) == 1
    assert len(dumped["citations"]) == 1
    assert len(dumped["assumptions"]) == 1
    assert len(dumped["limitations"]) == 1
    assert len(dumped["suggested_next_steps"]) == 1
