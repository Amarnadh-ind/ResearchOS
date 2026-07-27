"""
Agent input/output schemas — typed contracts between agents.
"""

from pydantic import BaseModel, Field


class PlannerInput(BaseModel):
    prompt: str
    depth: str = "standard"


class ResearchPlan(BaseModel):
    """Output of the Planner Agent."""

    research_question: str
    sub_questions: list[str]
    search_queries: list[str]
    methodology: str
    expected_sections: list[str]
    key_concepts: list[str]
    primary_topic: str | None = None
    secondary_topics: list[str] | None = None
    keywords: list[str] | None = None
    technical_domain: str | None = None


class SearchResult(BaseModel):
    """A single search result."""

    title: str
    url: str
    snippet: str
    relevance_score: float = Field(ge=0, le=1)
    source_quality: float = Field(default=0.5, ge=0, le=1)
    publication_date: str | None = None
    author: str | None = None


class SearchOutput(BaseModel):
    """Output of the Search Agent."""

    queries_executed: list[str]
    results: list[SearchResult]
    total_results: int


class BrowsedPage(BaseModel):
    """Content extracted from a web page."""

    url: str
    title: str
    content: str
    content_type: str = "text"  # text, pdf, html, markdown
    word_count: int = 0
    extraction_quality: float = Field(default=0.8, ge=0, le=1)
    publication_date: str | None = None
    author: str | None = None
    site_name: str | None = None
    description: str | None = None


class BrowserOutput(BaseModel):
    """Output of the Browser Agent."""

    pages: list[BrowsedPage]
    failed_urls: list[str] = Field(default_factory=list)


class ReadDocument(BaseModel):
    """A parsed and structured document."""

    source_url: str
    title: str
    sections: list[dict]  # {heading, content}
    key_findings: list[str]
    methodology: str | None = None
    summary: str


class ReaderOutput(BaseModel):
    """Output of the Reader Agent."""

    documents: list[ReadDocument]


class ExtractedClaim(BaseModel):
    """A single extracted claim with evidence."""

    claim: str
    evidence: str
    source_url: str
    source_title: str
    confidence: float = Field(ge=0, le=1)
    claim_type: str = "empirical"  # empirical, theoretical, methodological


class ClaimExtractionOutput(BaseModel):
    """Output of the Claim Extractor."""

    claims: list[ExtractedClaim]
    total_claims: int


class CritiqueResult(BaseModel):
    """Critique of a single claim."""

    claim: str
    is_valid: bool
    critique: str
    evidence_quality: str  # strong, moderate, weak, insufficient
    suggested_verification: str | None = None


class CriticOutput(BaseModel):
    """Output of the Critic Agent."""

    critiques: list[CritiqueResult]
    overall_evidence_quality: str
    rejected_claims: list[str]
    verified_claims: list[str]


class NoveltyAssessment(BaseModel):
    """Novelty analysis result."""

    novelty_score: float = Field(ge=0, le=1)
    novel_contributions: list[str]
    existing_work_overlap: list[str]
    research_gaps: list[str]
    suggested_angles: list[str]


class WriterOutput(BaseModel):
    """Output of the Writer Agent."""

    title: str
    abstract: str
    sections: list[dict]  # {heading, content, subsections}
    conclusion: str


class CitationEntry(BaseModel):
    """A formatted citation."""

    key: str  # e.g., "[1]"
    ieee_format: str
    authors: list[str]
    title: str
    publication: str | None = None
    year: int | None = None
    doi: str | None = None
    url: str
    verified: bool = False


class CitationOutput(BaseModel):
    """Output of the Citation Agent."""

    citations: list[CitationEntry]
    in_text_map: dict[str, str | None]  # claim_hash -> citation_key

class IEEEPaper(BaseModel):
    """Final IEEE-formatted paper."""

    title: str
    authors: list[str] = Field(default_factory=lambda: ["ResearchOS Autonomous System"])
    abstract: str
    keywords: list[str]
    sections: list[dict]
    references: list[str]
    content_markdown: str
    content_latex: str | None = None
