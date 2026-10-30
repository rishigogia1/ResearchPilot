import json
import logging
from typing import Any, Dict, List, Optional

from app.agent.evidence_processor import ProcessedEvidenceBundle
from app.agent.planner import ResearchPlan
from app.schemas.research import (
    Citation,
    ConfidenceLevel,
    ConfidenceScore,
    ExecutionStatus,
    FindingItem,
    ResearchResponse,
)
from app.services.llm_service import LLMService, LLMServiceError, llm_service

logger = logging.getLogger("researchpilot.agent.synthesizer")


class SynthesizerError(Exception):
    """Raised when answer synthesis fails."""
    pass


SYNTHESIZER_SYSTEM_PROMPT = """You are the Senior Research Synthesizer for ResearchPilot.
Your objective is to produce an authoritative, citation-grounded research report based EXCLUSIVELY on the provided web evidence.

CRITICAL GROUNDING RULES:
1. STRICT ADHERENCE TO EVIDENCE: Use only the facts, figures, and statements in the provided sources. Do not invent facts, URLs, quotes, or statistics from pretrained knowledge.
2. CITATION ANCHORING: Every key claim must reference its source ID (e.g., [src-1], [src-2]).
3. UNCERTAINTY & LIMITATIONS: If sources conflict, differ in methodology, or lack conclusive data, explicitly document this in the confidence explanation and limitations.
4. VALID JSON OUTPUT ONLY: Output ONLY valid JSON adhering to the specified schema.

JSON SCHEMA:
{
  "executive_summary": "Concise 2-4 sentence executive overview answering the core research question.",
  "findings": [
    {
      "heading": "Thematic Heading",
      "content": "Substantive analysis and details referencing [src-X].",
      "citations": ["src-1"]
    }
  ],
  "citations": [
    {
      "citation_id": "cite-1",
      "source_id": "src-1",
      "cited_claim": "The exact factual claim supported by this source"
    }
  ],
  "confidence_score": 0.85,
  "confidence_level": "high",
  "confidence_explanation": "Explanation for why confidence is rated high, medium, or low based on source quality and agreement.",
  "assumptions": ["Underlying assumptions made during analysis."],
  "limitations": ["Data gaps, timeframe constraints, or conflicting reports."],
  "suggested_next_steps": ["Recommendations for deeper follow-up investigation."]
}
"""


class AnswerSynthesizer:
    """Grounded answer synthesizer linking facts to verified citations."""

    def __init__(self, llm: Optional[LLMService] = None):
        self.llm = llm or llm_service

    async def synthesize(
        self,
        query: str,
        plan: ResearchPlan,
        evidence: ProcessedEvidenceBundle,
    ) -> ResearchResponse:
        """Synthesize final research response grounded in collected evidence."""
        # 1. Handle insufficient evidence upfront
        if evidence.is_insufficient or not evidence.sources:
            return self.synthesize_insufficient_evidence(query, plan, evidence.limitations)

        # 2. Build synthesis prompt
        user_prompt = (
            f"ORIGINAL RESEARCH QUESTION:\n{query}\n\n"
            f"RESEARCH OBJECTIVE:\n{plan.objective}\n\n"
            f"SUBQUESTIONS:\n" + "\n".join(f"- {sq}" for sq in plan.subquestions) + "\n\n"
            f"COLLECTED EVIDENCE SOURCES:\n{evidence.context_text}\n\n"
            "Produce the final structured research report adhering strictly to the JSON schema."
        )

        messages = [
            {"role": "system", "content": SYNTHESIZER_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

        logger.info("Synthesizing grounded answer for query '%s' with %d sources", query, len(evidence.sources))

        # Attempt synthesis with bounded correction
        for attempt in range(2):
            try:
                response = await self.llm.generate_json(messages=messages, temperature=0.1)
                data = response.parsed_json or {}
                return self._build_response_model(query, plan, evidence, data)
            except LLMServiceError:
                raise
            except Exception as exc:
                logger.warning("Synthesis attempt %d failed: %s", attempt + 1, str(exc))
                if attempt == 0:
                    messages.append({
                        "role": "user",
                        "content": "The previous output was malformed. Please return strictly valid JSON matching the schema.",
                    })
                else:
                    raise SynthesizerError(f"Failed to synthesize grounded answer: {str(exc)}") from exc

        raise SynthesizerError("Failed to synthesize research report.")

    def _build_response_model(
        self,
        query: str,
        plan: ResearchPlan,
        evidence: ProcessedEvidenceBundle,
        data: Dict[str, Any],
    ) -> ResearchResponse:
        """Assemble and validate ResearchResponse, validating citation source IDs."""
        source_lookup = {s.source_id: s for s in evidence.sources}

        executive_summary = (
            data.get("executive_summary")
            or "Research synthesis completed based on available web evidence."
        )

        raw_findings = data.get("findings", [])
        findings: List[FindingItem] = []
        if isinstance(raw_findings, list):
            for f in raw_findings:
                if isinstance(f, dict) and f.get("heading") and f.get("content"):
                    cites = f.get("citations", [])
                    valid_cites = [str(c) for c in cites if str(c) in source_lookup]
                    findings.append(
                        FindingItem(
                            heading=str(f["heading"]).strip(),
                            content=str(f["content"]).strip(),
                            citations=valid_cites,
                        )
                    )

        if not findings and evidence.sources:
            # Fallback finding if LLM omitted structured findings list
            findings.append(
                FindingItem(
                    heading="Primary Evidence Summary",
                    content=executive_summary,
                    citations=[evidence.sources[0].source_id],
                )
            )

        # Validate citations against actual collected sources (prevent fabricated source links)
        raw_citations = data.get("citations", [])
        citations: List[Citation] = []
        if isinstance(raw_citations, list):
            for idx, c in enumerate(raw_citations):
                if not isinstance(c, dict):
                    continue
                source_id = str(c.get("source_id", "")).strip()
                if source_id in source_lookup:
                    source = source_lookup[source_id]
                    citations.append(
                        Citation(
                            citation_id=f"cite-{idx + 1}",
                            source_id=source_id,
                            url=source.url,
                            source_title=source.title,
                            cited_claim=str(c.get("cited_claim", "")).strip() or "General finding attribution",
                        )
                    )

        # Confidence rating
        score = float(data.get("confidence_score", 0.75))
        score = max(0.0, min(1.0, score))

        level_str = str(data.get("confidence_level", "medium")).lower()
        if level_str in ("high", "medium", "low"):
            confidence_level = ConfidenceLevel(level_str)
        else:
            confidence_level = ConfidenceLevel.MEDIUM

        explanation = (
            data.get("confidence_explanation")
            or f"Confidence based on analysis of {len(evidence.sources)} retrieved web sources."
        )

        assumptions = [str(a) for a in data.get("assumptions", []) if str(a).strip()]
        combined_limitations = list(evidence.limitations)
        for lim in data.get("limitations", []):
            if str(lim).strip() and str(lim) not in combined_limitations:
                combined_limitations.append(str(lim).strip())

        suggested_next_steps = [str(s) for s in data.get("suggested_next_steps", []) if str(s).strip()]

        confidence = ConfidenceScore(
            score=score,
            level=confidence_level,
            explanation=explanation,
            limitations=combined_limitations,
        )

        return ResearchResponse(
            query=query,
            status=ExecutionStatus.COMPLETED,
            executive_summary=executive_summary,
            findings=findings,
            plan=plan.steps,
            sources=evidence.sources,
            citations=citations,
            confidence=confidence,
            assumptions=assumptions,
            limitations=combined_limitations,
            suggested_next_steps=suggested_next_steps,
            metadata={"sources_evaluated": evidence.total_sources_evaluated},
        )

    def synthesize_insufficient_evidence(
        self,
        query: str,
        plan: ResearchPlan,
        limitations: List[str],
    ) -> ResearchResponse:
        """Generate structured response when web search yielded insufficient verifiable facts."""
        all_limitations = list(limitations) or ["Search returned no accessible or relevant web sources."]

        return ResearchResponse(
            query=query,
            status=ExecutionStatus.COMPLETED,
            executive_summary=(
                f"Insufficient verifiable web evidence was found to thoroughly answer '{query}'. "
                "The search did not discover accessible, high-relevance pages answering the query."
            ),
            findings=[],
            plan=plan.steps,
            sources=[],
            citations=[],
            confidence=ConfidenceScore(
                score=0.15,
                level=ConfidenceLevel.LOW,
                explanation="No authoritative web sources could be accessed or extracted for this query.",
                limitations=all_limitations,
            ),
            assumptions=["Target domain or topic may have limited public web indexing or strict access barriers."],
            limitations=all_limitations,
            suggested_next_steps=[
                "Rephrase the question with alternate terminology or specific company/product names.",
                "Verify whether the topic requires access to proprietary databases or paywalled resources.",
            ],
            metadata={"status": "insufficient_evidence"},
        )


synthesizer = AnswerSynthesizer()
