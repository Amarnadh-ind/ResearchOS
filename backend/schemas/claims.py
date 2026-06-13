"""
Claim and evidence schemas for traceability.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class Evidence(BaseModel):
    """A piece of evidence supporting a claim."""
    text: str
    source_url: str
    source_title: str
    page_number: int | None = None
    extraction_method: str = "llm"  # llm, regex, manual


class Claim(BaseModel):
    """A research claim with full provenance chain."""
    id: UUID | None = None
    claim_text: str
    evidence: list[Evidence]
    confidence: float = Field(ge=0, le=1)
    verified: bool = False
    critique: str | None = None
    claim_type: str = "empirical"
    created_at: datetime = Field(default_factory=datetime.utcnow)

    def is_grounded(self) -> bool:
        """RULE-1: NO EVIDENCE = NO CLAIM"""
        return len(self.evidence) > 0 and self.confidence > 0.3


class Citation(BaseModel):
    """A verified citation with full metadata."""
    id: UUID | None = None
    citation_key: str
    ieee_format: str
    authors: list[str]
    title: str
    publication: str | None = None
    year: int | None = None
    doi: str | None = None
    url: str
    verified: bool = False

    def is_valid(self) -> bool:
        """RULE-2: NO SOURCE = NO CITATION"""
        return bool(self.url) and bool(self.title) and self.verified
