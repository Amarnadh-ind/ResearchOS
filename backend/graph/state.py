"""
Research State
TypedDict defining the full state flowing through the LangGraph pipeline.
"""

from typing import TypedDict, Annotated
from operator import add


class ResearchState(TypedDict, total=False):
    """Complete state of a research pipeline execution."""

    # ── Input ────────────────────────────────────────────
    session_id: str
    prompt: str
    depth: str
    max_sources: int
    pages: int
    layout: str
    font: str
    visual_mode: str
    page_budget: dict         # Word count targets per section
    target_word_count: int    # Total body word target
    expansion_round: int      # How many times content has been expanded
    topic_context: list[str]  # Topic context keywords for validation and grounding
    topic: str                # User topic
    primary_topic: str
    secondary_topics: list[str]
    keywords: list[str]
    technical_domain: str
    sources: list             # Active sources and citations
    validation: dict          # Validation results dictionary

    # ── Planner Output ───────────────────────────────────
    research_question: str
    sub_questions: list[str]
    search_queries: list[str]
    methodology: str
    expected_sections: list[str]
    key_concepts: list[str]

    # ── Search Output ────────────────────────────────────
    search_results: list[dict]

    # ── Browser Output ───────────────────────────────────
    browsed_pages: list[dict]
    failed_urls: list[str]

    # ── Reader Output ────────────────────────────────────
    documents: list[dict]

    # ── Claim Extraction ─────────────────────────────────
    claims: list[dict]
    total_claims: int

    # ── Critic Output ────────────────────────────────────
    critiques: list[dict]
    overall_evidence_quality: str
    rejected_claims: list[str]
    verified_claims: list[str]

    # ── Novelty Output ───────────────────────────────────
    novelty_score: float
    novel_contributions: list[str]
    research_gaps: list[str]

    # ── Citation Output ──────────────────────────────────
    citations: list[dict]
    in_text_map: dict[str, str]
    citation_agent_input: dict
    citation_agent_output: dict
    citation_agent_error: str
    writer_citation_status: str

    # ── Writer Output ────────────────────────────────────
    paper_title: str
    paper_abstract: str
    paper_sections: list[dict]
    paper_conclusion: str

    # ── IEEE Output ──────────────────────────────────────
    final_paper: dict
    content_markdown: str

    # ── Pipeline Control ─────────────────────────────────
    relevance_attempts: int
    current_agent: str
    status: str
    error: str | None
    events: Annotated[list[dict], add]
