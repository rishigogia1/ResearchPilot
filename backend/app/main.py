import logging
import time
import uuid
from typing import Any
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1 import api_v1_router
from app.api.v1.health import get_general_health
from app.config import settings
from app.schemas.research import HealthResponse

# Configure structured application logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
)
logger = logging.getLogger("researchpilot")

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Full-stack AI Research Agent API with Grounded Web Search & Citation Validation",
)

# Configure CORS using settings.frontend_origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.frontend_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==============================================================================
# Middleware: Request Correlation ID & Processing Timing
# ==============================================================================

@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.request_id = request_id
    start_time = time.perf_counter()

    try:
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time-Ms"] = str(duration_ms)

        logger.info(
            "REQ END: %s %s -> status=%d duration=%.2fms [request_id=%s]",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            request_id,
        )
        return response
    except Exception as exc:
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        logger.error(
            "REQ FAIL: %s %s failed after %.2fms [request_id=%s]: %s",
            request.method,
            request.url.path,
            duration_ms,
            request_id,
            str(exc),
            exc_info=True,
        )
        raise exc


# ==============================================================================
# Exception Handlers: Safe, Structured Error Responses (No Stack Trace Leaks)
# ==============================================================================

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    formatted_errors = []
    for err in exc.errors():
        field = ".".join(str(loc) for loc in err.get("loc", []) if loc != "body")
        formatted_errors.append({
            "field": field or "body",
            "message": err.get("msg", "Invalid value"),
            "type": err.get("type", "value_error"),
        })

    logger.warning("Validation error on %s [request_id=%s]: %s", request.url.path, request_id, formatted_errors)
    return JSONResponse(
        status_code=422,
        headers={"X-Request-ID": request_id},
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Input validation failed. Please check the request parameters.",
                "details": formatted_errors,
                "request_id": request_id,
            }
        },
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    
    code = "HTTP_ERROR"
    message = str(exc.detail)
    details: Any = None

    if isinstance(exc.detail, dict):
        code = exc.detail.get("code", "HTTP_ERROR")
        message = exc.detail.get("message", "An error occurred.")
        details = exc.detail.get("details")
        if not details and len(exc.detail) > 2:
            # Include extra metadata if present
            details = {k: v for k, v in exc.detail.items() if k not in ("code", "message")}

    return JSONResponse(
        status_code=exc.status_code,
        headers={"X-Request-ID": request_id},
        content={
            "error": {
                "code": code,
                "message": message,
                "details": details,
                "request_id": request_id,
            }
        },
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    logger.error("Unhandled server exception [request_id=%s]: %s", request_id, str(exc), exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        headers={"X-Request-ID": request_id},
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected server error occurred. Please try again later.",
                "details": None,
                "request_id": request_id,
            }
        },
    )


# ==============================================================================
# Base Routes
# ==============================================================================

@app.get("/", tags=["General"])
async def root():
    return {
        "message": "Welcome to ResearchPilot API",
        "docs_url": "/docs",
        "health_url": "/health",
        "version": settings.app_version,
    }


# Root /health alias for top-level health probes
@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def root_health():
    return await get_general_health()


# Mount versioned API routes
app.include_router(api_v1_router)
