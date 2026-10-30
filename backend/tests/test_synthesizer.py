import pytest
from unittest.mock import AsyncMock
from app.agent.evidence_processor import ProcessedEvidenceBundle
from app.agent.planner import ResearchPlan
from app.agent.synthesizer import AnswerSynthesizer, SynthesizerError
from app.schemas.research import ConfidenceLevel, EvidenceSource, ExecutionStatus
from app.services.llm_service import LLMResponse


@pytest.mark.asyncio
async def test_synthesizer_grounded_answer():
    mock_llm = AsyncMock()
    mock_llm.generate_json.return_value = LLMResponse(
        content="{}",
        parsed_json={
            "executive_summary": "Solid-state batteries demonstrate higher safety margins and energy density.",
            "findings": [
                {
                    "heading": "Electrolyte Stability",
                    "content": "Sulfide-based solid electrolytes achieve ionic conductivity comparable to liquids [src-1].",
                    "citations": ["src-1"],
                }
            ],
            "citations": [
                {
                    "citation_id": "cite-1",
                    "source_id": "src-1",
                    "cited_claim": "Sulfide-based electrolytes match liquid ionic conductivity",
                },
                {
                    "citation_id": "cite-hallucinated",
                    "source_id": "src-999",  # Non-existent source
                    "cited_claim": "Hallucinated claim",
                },
            ],
            "confidence_score": 0.88,
            "confidence_level": "high",
            "confidence_explanation": "Corroborated by academic and industry lab reports.",
            "assumptions": ["Testing was performed at ambient pressure."],
            "limitations": ["Dendrite growth at lithium anode interface remains a manufacturing hurdle."],
            "suggested_next_steps": ["Analyze high-pressure cell stack designs."],
        },
        provider="openai",
        model="gpt-4o-mini",
        latency_ms=250.0,
    )

    plan = ResearchPlan(
        objective="Assess solid state battery electrolytes",
        subquestions=["What ionic conductivity is achieved?"],
        search_queries=["solid state battery electrolyte conductivity"],
    )

    evidence = ProcessedEvidenceBundle(
        sources=[
            EvidenceSource(
                source_id="src-1",
                url="https://example.org/solid-state-paper",
                title="Solid State Electrolytes",
                domain="example.org",
                snippet="Sulfide conductors reach 10 mS/cm.",
                raw_content="Detailed measurements confirm ionic conductivity of sulfide conductors...",
            )
        ],
        total_sources_evaluated=1,
        retained_sources_count=1,
        is_insufficient=False,
        context_text="Source content...",
    )

    synthesizer = AnswerSynthesizer(llm=mock_llm)
    res = await synthesizer.synthesize(
        query="Solid state battery electrolyte progress",
        plan=plan,
        evidence=evidence,
    )

    assert res.status == ExecutionStatus.COMPLETED
    assert "Solid-state batteries" in res.executive_summary
    assert len(res.findings) == 1
    assert res.findings[0].citations == ["src-1"]
    # Verify hallucinated citation "src-999" was purged
    assert len(res.citations) == 1
    assert res.citations[0].source_id == "src-1"
    assert res.citations[0].url == "https://example.org/solid-state-paper"
    assert res.confidence.level == ConfidenceLevel.HIGH
    assert res.confidence.score == 0.88


@pytest.mark.asyncio
async def test_synthesizer_insufficient_evidence_flow():
    plan = ResearchPlan(
        objective="Investigate query with no evidence",
        subquestions=["Question 1"],
        search_queries=["query 1"],
    )

    evidence = ProcessedEvidenceBundle(
        sources=[],
        is_insufficient=True,
        limitations=["Search engine returned 0 results."],
    )

    synthesizer = AnswerSynthesizer()
    res = await synthesizer.synthesize(
        query="Query with no evidence",
        plan=plan,
        evidence=evidence,
    )

    assert res.status == ExecutionStatus.COMPLETED
    assert "Insufficient verifiable web evidence" in res.executive_summary
    assert res.confidence.level == ConfidenceLevel.LOW
    assert len(res.sources) == 0
    assert len(res.findings) == 0
    assert len(res.suggested_next_steps) > 0


@pytest.mark.asyncio
async def test_synthesizer_fails_on_unrecoverable_llm_error():
    mock_llm = AsyncMock()
    mock_llm.generate_json.side_effect = Exception("Unrecoverable error")

    plan = ResearchPlan(
        objective="Test objective",
        subquestions=["Subq 1"],
        search_queries=["search 1"],
    )

    evidence = ProcessedEvidenceBundle(
        sources=[
            EvidenceSource(
                source_id="src-1",
                url="https://example.org/1",
                title="Title",
                domain="example.org",
                snippet="Snippet text",
                raw_content="Content text",
            )
        ],
        is_insufficient=False,
        context_text="Context block",
    )

    synthesizer = AnswerSynthesizer(llm=mock_llm)
    with pytest.raises(SynthesizerError):
        await synthesizer.synthesize(query="Test query", plan=plan, evidence=evidence)
