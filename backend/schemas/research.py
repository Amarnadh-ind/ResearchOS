"""
Research session schemas.
"""

from datetime import datetime
try:
    from enum import StrEnum
except ImportError:
    from enum import Enum

    class StrEnum(str, Enum):  # noqa: UP042
        pass
from uuid import UUID

from pydantic import BaseModel, Field


class ResearchStatus(StrEnum):
    PENDING = "pending"
    PLANNING = "planning"
    SEARCHING = "searching"
    BROWSING = "browsing"
    READING = "reading"
    EXTRACTING = "extracting"
    CRITIQUING = "critiquing"
    ANALYZING_NOVELTY = "analyzing_novelty"
    WRITING = "writing"
    CITING = "citing"
    FORMATTING = "formatting"
    COMPLETED = "completed"
    FAILED = "failed"


class ResearchRequest(BaseModel):
    """Input: a research prompt from the user."""
    prompt: str = Field(..., min_length=10, max_length=5000, description="Research question or topic")
    depth: str = Field(default="standard", description="Research depth: quick, standard, deep")
    max_sources: int = Field(default=20, ge=1, le=100, description="Maximum sources to gather")
    output_format: str = Field(default="ieee", description="Paper format: ieee, apa, chicago")
    pages: int = Field(default=12, ge=1, le=100, description="Target page count for the paper")
    layout: str = Field(default="2 Column", description="Layout of the paper: 1 Column, 2 Column, Multi Column")
    font: str = Field(default="Times New Roman", description="Font name")
    visual_mode: str = Field(default="Mixed", description="Visual content mode: Auto, Manual, Mixed")


class ResearchResponse(BaseModel):
    """Response after initiating research."""
    session_id: UUID
    status: ResearchStatus
    message: str


class ResearchSession(BaseModel):
    """Full research session state."""
    id: UUID
    prompt: str
    status: ResearchStatus
    plan: dict | None = None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None
    error: str | None = None


class AgentEvent(BaseModel):
    """Real-time event from agent pipeline."""
    session_id: UUID
    agent_name: str
    event_type: str  # 'started', 'progress', 'completed', 'error'
    data: dict = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ResearchProgress(BaseModel):
    """Overall pipeline progress."""
    session_id: UUID
    status: ResearchStatus
    current_agent: str
    agents_completed: list[str]
    agents_remaining: list[str]
    progress_pct: float = Field(ge=0, le=100)
    sources_found: int = 0
    claims_extracted: int = 0
