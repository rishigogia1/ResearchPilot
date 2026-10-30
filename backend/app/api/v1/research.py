import logging
from fastapi import APIRouter, HTTPException, status
from app.agent.orchestrator import OrchestratorError, orchestrator
from app.schemas.research import (
    ErrorResponse,
    ResearchRequest,
    ResearchResponse,
)

logger = logging.getLogger("researchpilot.api.research")
router = APIRouter()


@router.post(
    "",
    response_model=ResearchResponse,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "model": ErrorResponse,
            "description": "Required credentials unconfigured or external service unavailable.",
        },
        status.HTTP_504_GATEWAY_TIMEOUT: {
            "model": ErrorResponse,
            "description": "Research workflow timed out.",
        },
        422: {
            "description": "Validation error for empty or invalid research queries.",
        },
    },
)
async def conduct_research(request: ResearchRequest) -> ResearchResponse:
    """
    Execute full autonomous research workflow.
    Validates request, plans investigation, executes live searches, retrieves content,
    processes grounded evidence, and returns structured citation findings.
    """
    logger.info(
        "Received research request: query='%s', depth=%s, max_sources=%d",
        request.query,
        request.depth.value,
        request.max_sources,
    )

    try:
        response = await orchestrator.execute_research(request)
        return response

    except OrchestratorError as orch_err:
        logger.warning("Research orchestration error [%s]: %s", orch_err.code, orch_err.message)
        if orch_err.code == "MISSING_CREDENTIALS":
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "code": "MISSING_CREDENTIALS",
                    "message": orch_err.message,
                },
            )
        elif orch_err.code == "RATE_LIMITED":
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "code": "RATE_LIMITED",
                    "message": orch_err.message,
                },
            )
        elif orch_err.code == "WORKFLOW_TIMEOUT":
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail={
                    "code": "WORKFLOW_TIMEOUT",
                    "message": orch_err.message,
                },
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail={
                    "code": orch_err.code,
                    "message": orch_err.message,
                },
            )
    except Exception as exc:
        logger.error("Unhandled error during research execution: %s", str(exc), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "EXECUTION_FAILURE",
                "message": "An unexpected error occurred during research execution.",
            },
        )
