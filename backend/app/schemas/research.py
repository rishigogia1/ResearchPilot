from datetime import datetime, timezone
from enum import Enum
from typing import Any, List, Optional
from pydantic import BaseModel, Field, field_validator


class ExecutionStatus(str, Enum):
    """Execution state of a research job."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    NOT_IMPLEMENTED = "not_implemented"


class ConfidenceLevel(str, Enum):
    """Categorical confidence level of synthesized findings."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ResearchDepth(str, Enum):
    """Depth levels for research orchestration."""
    QUICK = "quick"
    STANDARD = "standard"
    DEEP = "deep"


class ServiceStatus(str, Enum):
    """Operational/configuration status of an external service or tool."""
    MISSING_CREDENTIALS = "missing_credentials"
    CONFIGURED = "configured"
    VERIFIED = "verified"
    UNAVAILABLE = "unavailable"


# ==============================================================================
# Health Check Schemas
# ==============================================================================

class HealthResponse(BaseModel):
    """General system health check response."""
    status: str = "ok"
    app: str = "ResearchPilot API"
    version: str = "0.1.0"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    services: dict = Field(default_factory=dict)


class LLMHealthResponse(BaseModel):
    """LLM provider health and configuration status."""
    status: ServiceStatus
    configured: bool
    provider: str
    model: str
    message: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ToolItemHealth(BaseModel):
    """Health item for an individual research tool."""
    name: str
    status: ServiceStatus
    configured: bool
    verified: bool
    description: str


class ToolsHealthResponse(BaseModel):
    """Tool ecosystem health check response."""
    status: str
    tools: List[ToolItemHealth]
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ==============================================================================
# Error Schemas
# ==============================================================================

class ErrorDetail(BaseModel):
    """Standardized error details."""
    code: str
    message: str
    details: Optional[Any] = None
    request_id: Optional[str] = None


class ErrorResponse(BaseModel):
    """Root error response wrapper."""
    error: ErrorDetail


# ==============================================================================
# Research Domain Schemas
# ==============================================================================

class ResearchRequest(BaseModel):
    """Incoming user research request validation schema."""
    query: str = Field(
        ...,
        min_length=3,
        max_length=1000,
        description="The research question or topic (3 to 1000 characters).",
    )
    depth: ResearchDepth = Field(
        default=ResearchDepth.STANDARD,
        description="Research thoroughness level.",
    )
    max_sources: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum number of sources to explore (between 1 and 20).",
    )

    @field_validator("query")
    @classmethod
    def validate_query(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 3:
            raise ValueError("Research question must contain at least 3 non-whitespace characters.")
        return cleaned


class PlanStep(BaseModel):
    """An individual step in the research plan."""
    step_id: int
    description: str
    search_query: str
    status: str = "pending"  # pending, running, completed, failed


class EvidenceSource(BaseModel):
    """Retrieved source evidence with content extract."""
    source_id: str
    url: str
    title: str
    domain: str
    snippet: str
    raw_content: Optional[str] = None
    credibility_note: Optional[str] = None


class Citation(BaseModel):
    """Inline or structured citation linking statement to source."""
    citation_id: str
    source_id: str
    url: str
    source_title: str
    cited_claim: str


class FindingItem(BaseModel):
    """A synthesized finding or key takeaway."""
    heading: str
    content: str
    citations: List[str] = Field(default_factory=list)


class ConfidenceScore(BaseModel):
    """Agent's confidence assessment of the findings."""
    score: float = Field(..., ge=0.0, le=1.0, description="Confidence score from 0.0 to 1.0.")
    level: ConfidenceLevel = Field(
        default=ConfidenceLevel.MEDIUM,
        description="Categorical confidence rating.",
    )
    explanation: str
    limitations: List[str] = Field(default_factory=list)


class ResearchResponse(BaseModel):
    """Complete research response synthesized by the agent."""
    query: str
    status: ExecutionStatus = ExecutionStatus.COMPLETED
    executive_summary: str
    findings: List[FindingItem] = Field(default_factory=list)
    plan: List[PlanStep] = Field(default_factory=list)
    sources: List[EvidenceSource] = Field(default_factory=list)
    citations: List[Citation] = Field(default_factory=list)
    confidence: ConfidenceScore
    assumptions: List[str] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)
    suggested_next_steps: List[str] = Field(default_factory=list)
    completed_at: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc))
    execution_time_seconds: Optional[float] = None
    metadata: dict = Field(default_factory=dict)
