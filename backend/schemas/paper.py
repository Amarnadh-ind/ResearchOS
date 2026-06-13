"""
Paper structure schemas.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class PaperSection(BaseModel):
    """A section of the research paper."""
    heading: str
    content: str
    subsections: list["PaperSection"] = Field(default_factory=list)
    order: int = 0


class PaperDraft(BaseModel):
    """A complete research paper draft."""
    id: UUID | None = None
    session_id: UUID | None = None
    title: str
    abstract: str
    keywords: list[str] = Field(default_factory=list)
    sections: list[PaperSection]
    references: list[str]
    format: str = "ieee"
    version: int = 1
    content_markdown: str = ""
    content_latex: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
