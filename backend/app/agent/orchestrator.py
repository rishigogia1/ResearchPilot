import asyncio
import logging
import time
from typing import List, Optional

from app.agent.evidence_processor import EvidenceProcessor, evidence_processor
from app.agent.planner import PlannerError, ResearchPlan, ResearchPlanner, planner
from app.agent.synthesizer import AnswerSynthesizer, SynthesizerError, synthesizer
from app.services.llm_service import LLMCredentialsError, LLMServiceError
from app.config import settings
from app.schemas.research import (
    ExecutionStatus,
    PlanStep,
    ResearchRequest,
    ResearchResponse,
)
from app.tools.web_search import (
    SearchResultItem,
    SearchToolError,
    TavilyCredentialsError,
    TavilySearchTool,
    tavily_search_tool,
)
from app.tools.webpage_reader import ExtractedPage, WebpageReader, webpage_reader

logger = logging.getLogger("researchpilot.agent.orchestrator")


class OrchestratorError(Exception):
    """Raised when research orchestration fails."""
    def __init__(self, message: str, code: str = "ORCHESTRATION_ERROR"):
        super().__init__(message)
        self.code = code
        self.message = message


class ResearchOrchestrator:
    """
    Core research orchestrator executing an explicit 10-step pipeline:
    Plan -> Validate -> Search -> Deduplicate -> Extract -> Process Evidence ->
    Synthesize -> Validate Citations -> Return Verified Response.
    """

    def __init__(
        self,
        plan_generator: Optional[ResearchPlanner] = None,
        search_engine: Optional[TavilySearchTool] = None,
        page_reader: Optional[WebpageReader] = None,
        evidence_proc: Optional[EvidenceProcessor] = None,
        answer_synth: Optional[AnswerSynthesizer] = None,
    ):
        self.planner = plan_generator or planner
        self.search_tool = search_engine or tavily_search_tool
        self.reader = page_reader or webpage_reader
        self.evidence_processor = evidence_proc or evidence_processor
        self.synthesizer = answer_synth or synthesizer

    async def execute_research(self, request: ResearchRequest) -> ResearchResponse:
        """
        Execute full autonomous research workflow with bounded concurrency,
        timeout guards, and resilient partial-failure handling.
        """
        start_time = time.perf_counter()
        logger.info(
            "Starting research workflow for query: '%s' (depth=%s, max_sources=%d)",
            request.query,
            request.depth.value,
            request.max_sources,
        )

        # Enforce server-side overall timeout
        timeout = getattr(settings, "research_timeout_seconds", 90.0)

        try:
            return await asyncio.wait_for(
                self._run_pipeline(request, start_time),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            duration = round(time.perf_counter() - start_time, 2)
            logger.error("Research workflow exceeded timeout of %.1fs [duration=%.2fs]", timeout, duration)
            raise OrchestratorError(
                f"Research execution exceeded the timeout limit of {timeout} seconds.",
                code="WORKFLOW_TIMEOUT",
            )
        except OrchestratorError:
            raise
        except Exception as exc:
            duration = round(time.perf_counter() - start_time, 2)
            logger.error("Research workflow unhandled error [duration=%.2fs]: %s", duration, str(exc), exc_info=True)
            raise OrchestratorError(f"Research pipeline failed: {type(exc).__name__}: {str(exc)}")

    async def _run_pipeline(self, request: ResearchRequest, start_time: float) -> ResearchResponse:
        # Step 1 & 2: Generate Research Plan
        try:
            plan: ResearchPlan = await self.planner.create_plan(
                query=request.query,
                depth=request.depth,
                max_sources=request.max_sources,
            )
        except LLMServiceError as llm_err:
            logger.warning("Planning failed due to LLM error [%s]: %s", llm_err.code, llm_err.message)
            raise OrchestratorError(llm_err.message, code=llm_err.code)
        except Exception as exc:
            # Check if inner error is credentials error
            if "credentials" in str(exc).lower() or "api key is missing" in str(exc).lower():
                raise OrchestratorError(str(exc), code="MISSING_CREDENTIALS")
            logger.error("Planning phase failed: %s", str(exc))
            raise OrchestratorError(f"Failed to generate research plan: {str(exc)}", code="PLANNING_FAILED")

        # Step 3: Validate and log plan steps
        logger.info(
            "Plan generated successfully: %d steps, %d queries",
            len(plan.steps),
            len(plan.search_queries),
        )

        # Step 4: Execute search queries concurrently (bounded)
        search_tasks = []
        for step in plan.steps:
            step.status = "running"
            search_tasks.append(
                self._execute_single_search(step, max_results=request.max_sources)
            )

        search_responses = await asyncio.gather(*search_tasks, return_exceptions=True)

        # Step 5: Collect and deduplicate search results
        all_search_results: List[SearchResultItem] = []
        successful_searches = 0
        failed_searches = 0

        for idx, res in enumerate(search_responses):
            step = plan.steps[idx]
            if isinstance(res, Exception):
                step.status = "failed"
                failed_searches += 1
                logger.warning("Search query failed for step %d ('%s'): %s", step.step_id, step.search_query, str(res))
            else:
                step.status = "completed"
                successful_searches += 1
                all_search_results.extend(res)

        # If ALL searches failed, we cannot proceed with fabricated findings
        if successful_searches == 0 and len(plan.steps) > 0:
            first_err = search_responses[0] if search_responses else "Unknown error"
            if isinstance(first_err, TavilyCredentialsError):
                raise OrchestratorError(
                    "Tavily search API key is unconfigured. Please configure TAVILY_API_KEY in backend/.env.",
                    code="MISSING_CREDENTIALS",
                )
            raise OrchestratorError(
                f"All search queries failed during research: {str(first_err)}",
                code="SEARCH_FAILED",
            )

        # Deduplicate search results by URL
        seen_urls = set()
        deduped_search_results: List[SearchResultItem] = []
        for sr in all_search_results:
            if sr.url and sr.url not in seen_urls:
                seen_urls.add(sr.url)
                deduped_search_results.append(sr)

        logger.info(
            "Collected %d total search results (%d unique URLs) from %d successful queries",
            len(all_search_results),
            len(deduped_search_results),
            successful_searches,
        )

        # Step 6: Retrieve content from relevant discovered pages
        # Cap URLs to inspect
        target_urls = [sr.url for sr in deduped_search_results[: request.max_sources]]
        extracted_pages: List[ExtractedPage] = []

        if target_urls:
            logger.info("Extracting content from %d target web pages", len(target_urls))
            try:
                extracted_pages = await self.reader.fetch_multiple_pages(target_urls)
            except Exception as read_err:
                logger.warning("Page extraction encountered error: %s (falling back to snippets)", str(read_err))

        # Step 7: Process evidence (filtering, scoring, context budgeting)
        evidence_bundle = self.evidence_processor.process(
            query=request.query,
            subquestions=plan.subquestions,
            search_results=deduped_search_results,
            extracted_pages=extracted_pages,
            max_sources=request.max_sources,
        )

        # Step 8: Synthesize answer
        try:
            response: ResearchResponse = await self.synthesizer.synthesize(
                query=request.query,
                plan=plan,
                evidence=evidence_bundle,
            )
        except LLMServiceError as llm_err:
            logger.error("Synthesis failed due to LLM error [%s]: %s", llm_err.code, llm_err.message)
            raise OrchestratorError(llm_err.message, code=llm_err.code)
        except Exception as synth_err:
            logger.error("Synthesis failed: %s", str(synth_err))
            raise OrchestratorError(f"Failed to synthesize research report: {str(synth_err)}", code="SYNTHESIS_FAILED")

        # Step 9 & 10: Final validation, metadata, and execution timing
        execution_time = round(time.perf_counter() - start_time, 2)
        response.execution_time_seconds = execution_time
        response.plan = plan.steps

        # Mark partial if any tool failures occurred
        if failed_searches > 0:
            response.limitations.append(
                f"Partial search failure: {failed_searches} of {len(plan.steps)} planned searches could not be completed."
            )
            response.metadata["partial_result"] = True

        response.metadata["execution_time_seconds"] = execution_time
        response.metadata["successful_searches"] = successful_searches
        response.metadata["failed_searches"] = failed_searches
        response.metadata["sources_retained"] = len(response.sources)

        logger.info(
            "Research workflow completed in %.2fs: %d findings, %d sources, %d citations (confidence=%.2f)",
            execution_time,
            len(response.findings),
            len(response.sources),
            len(response.citations),
            response.confidence.score,
        )

        return response

    async def _execute_single_search(self, step: PlanStep, max_results: int) -> List[SearchResultItem]:
        """Execute single search query for a plan step."""
        res = await self.search_tool.search(
            query=step.search_query,
            max_results=max_results,
        )
        return res.results


orchestrator = ResearchOrchestrator()
