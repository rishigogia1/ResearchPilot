import logging
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator

from app.config import settings
from app.schemas.research import PlanStep, ResearchDepth
from app.services.llm_service import LLMService, LLMServiceError, llm_service

logger = logging.getLogger("researchpilot.agent.planner")


class PlannerError(Exception):
    """Raised when research plan generation fails."""
    pass


class ResearchPlan(BaseModel):
    """Structured plan generated dynamically for a research request."""
    objective: str = Field(..., description="The core research objective.")
    subquestions: List[str] = Field(..., min_length=1, description="Decomposed research subquestions.")
    search_queries: List[str] = Field(..., min_length=1, description="Specific queries for the search engine.")
    required_tools: List[str] = Field(
        default=["tavily_search", "web_extractor"],
        description="Tools needed to fulfill the plan.",
    )
    expected_report_format: str = Field(
        default="Executive summary with thematic findings and source citations.",
        description="Expected report structure.",
    )
    assumptions: List[str] = Field(default_factory=list, description="Initial planning assumptions.")
    steps: List[PlanStep] = Field(default_factory=list, description="Ordered execution steps.")
    max_sources: int = Field(default=5)
    max_execution_time_seconds: float = Field(default=30.0)

    @field_validator("search_queries")
    @classmethod
    def validate_search_queries(cls, queries: List[str]) -> List[str]:
        cleaned = [q.strip() for q in queries if q and q.strip()]
        if not cleaned:
            raise ValueError("Plan must contain at least one valid search query.")
        return cleaned


PLANNER_SYSTEM_PROMPT = """You are the Senior Research Planner for ResearchPilot, an autonomous research assistant.
Your job is to decompose the user's research question into an actionable, methodical investigation plan.

You must respond ONLY with a valid JSON object matching this schema:
{{
  "objective": "Clear statement of what this research aims to discover",
  "subquestions": ["Subquestion 1", "Subquestion 2"],
  "search_queries": ["Search query 1", "Search query 2"],
  "required_tools": ["tavily_search", "web_extractor"],
  "expected_report_format": "Executive summary with thematic findings and source citations.",
  "assumptions": ["Assumption 1"]
}}

Guidelines:
1. Generate specific, high-yield search queries (keywords, phrases, exact terminology).
2. Avoid generic queries like "tell me about X". Use targeted queries like "X benchmark comparison results 2025".
3. Provide between 1 and {max_queries} search queries.
4. Keep subquestions focused on answering the user's specific query.
"""


class ResearchPlanner:
    """Dynamic research plan generator using LLM."""

    def __init__(self, llm: Optional[LLMService] = None):
        self.llm = llm or llm_service

    async def create_plan(
        self,
        query: str,
        depth: ResearchDepth = ResearchDepth.STANDARD,
        max_sources: Optional[int] = None,
    ) -> ResearchPlan:
        """
        Dynamically plan research strategy for a given user query.
        Enforces server-side bounds on queries and sources.
        """
        # Determine server-side bounds
        server_max_queries = settings.max_search_queries
        if depth == ResearchDepth.QUICK:
            allowed_queries = min(2, server_max_queries)
        elif depth == ResearchDepth.DEEP:
            allowed_queries = min(server_max_queries, 5)
        else:
            allowed_queries = min(server_max_queries, 3)

        effective_max_sources = min(
            max_sources or settings.max_sources,
            settings.max_sources,
            20,
        )

        prompt = (
            f"Research Question: {query}\n"
            f"Research Depth: {depth.value}\n"
            f"Maximum Search Queries Allowed: {allowed_queries}\n"
            f"Maximum Sources to Review: {effective_max_sources}"
        )

        messages = [
            {"role": "system", "content": PLANNER_SYSTEM_PROMPT.format(max_queries=allowed_queries)},
            {"role": "user", "content": prompt},
        ]

        logger.info("Generating research plan for query: '%s' (depth=%s)", query, depth.value)

        # Attempt planning with bounded retry/recovery
        parsed_data: Optional[Dict[str, Any]] = None
        for attempt in range(2):
            try:
                response = await self.llm.generate_json(messages=messages, temperature=0.1)
                parsed_data = response.parsed_json or {}
                # Validate schema
                plan = self._build_plan_model(
                    parsed_data=parsed_data,
                    original_query=query,
                    allowed_queries=allowed_queries,
                    effective_max_sources=effective_max_sources,
                )
                return plan
            except LLMServiceError:
                raise
            except Exception as exc:
                logger.warning("Planner attempt %d failed: %s", attempt + 1, str(exc))
                if attempt == 0:
                    # Provide recovery prompt
                    messages.append({"role": "assistant", "content": str(parsed_data or "{}")})
                    messages.append({
                        "role": "user",
                        "content": "The previous JSON output was invalid. Please return strictly valid JSON matching the requested schema with non-empty search_queries.",
                    })
                else:
                    raise PlannerError(f"Failed to generate valid research plan: {str(exc)}") from exc

        raise PlannerError("Failed to generate research plan.")

    def _build_plan_model(
        self,
        parsed_data: Dict[str, Any],
        original_query: str,
        allowed_queries: int,
        effective_max_sources: int,
    ) -> ResearchPlan:
        """Enforce server-side bounds and build ResearchPlan instance."""
        objective = parsed_data.get("objective") or f"Investigate: {original_query}"
        subquestions = parsed_data.get("subquestions")
        if not subquestions or not isinstance(subquestions, list):
            subquestions = [f"What are the key facts regarding {original_query}?"]

        search_queries = parsed_data.get("search_queries")
        if not search_queries or not isinstance(search_queries, list):
            search_queries = [original_query]

        # Enforce server-side query limit
        bounded_queries = [str(q).strip() for q in search_queries if str(q).strip()][:allowed_queries]
        if not bounded_queries:
            bounded_queries = [original_query]

        required_tools = parsed_data.get("required_tools") or ["tavily_search", "web_extractor"]
        report_format = parsed_data.get("expected_report_format") or "Executive summary with thematic findings and source citations."
        assumptions = parsed_data.get("assumptions") or []
        if not isinstance(assumptions, list):
            assumptions = []

        # Build executable plan steps
        steps = [
            PlanStep(
                step_id=i + 1,
                description=f"Execute web search query: {q}",
                search_query=q,
                status="pending",
            )
            for i, q in enumerate(bounded_queries)
        ]

        return ResearchPlan(
            objective=str(objective),
            subquestions=[str(sq) for sq in subquestions],
            search_queries=bounded_queries,
            required_tools=[str(t) for t in required_tools],
            expected_report_format=str(report_format),
            assumptions=[str(a) for a in assumptions],
            steps=steps,
            max_sources=effective_max_sources,
            max_execution_time_seconds=settings.request_timeout_seconds * 2,
        )


planner = ResearchPlanner()
