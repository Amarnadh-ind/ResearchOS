"""
LangGraph Research Workflow
Defines the StateGraph for the research pipeline.

Pipeline (SEQUENTIAL — no broken parallelism):
Prompt -> Planner -> Search -> Firecrawl -> Reader -> ClaimExtractor
       -> Critic -> Citation+Novelty (parallel, safe) -> Writer
       -> CriticPaper -> WriterRevision -> IEEEFormatter
       -> Humanizer -> PageValidator -> Done
"""

import asyncio

import structlog
from langgraph.graph import END, START, StateGraph

from graph.nodes import (
    citation_node,
    claim_extractor_node,
    critic_node,
    critic_paper_node,
    firecrawl_extract_node,
    humanizer_node,
    ieee_formatter_node,
    novelty_node,
    page_validation_node,
    planner_node,
    reader_node,
    search_node,
    writer_node,
    writer_revision_node,
)
from graph.state import ResearchState

logger = structlog.get_logger()


def should_continue(state: ResearchState) -> str:
    """Route based on current_agent. Stops on failure."""
    status = state.get("status", "")
    if status == "failed":
        return END

    agent = state.get("current_agent", "")
    route_map = {
        # Sequential pipeline — each node routes to the next
        "planner": "search",
        "search": "firecrawl_extract",
        "firecrawl_extract": "reader",
        "reader": "claim_extractor",
        "claim_extractor": "critic",
        "critic": "citation_novelty",
        "citation_novelty": "writer",
        "writer": "critic_paper",
        "critic_paper": "writer_revision",
        "writer_revision": "ieee_formatter",
        "ieee_formatter": "humanizer",
        "humanizer": "page_validator",
        "page_validator": "done",

        # Terminal
        "done": END,
    }
    result = route_map.get(agent, END)
    logger.info("workflow_routing", current_agent=agent, next_node=result)
    return result


async def _citation_novelty_parallel_executor(state: ResearchState) -> dict:
    """Execute Citation and Novelty in parallel.
    These are safe to parallelize — both only read existing state."""
    citation_task = citation_node(state)
    novelty_task = novelty_node(state)

    citation_result, novelty_result = await asyncio.gather(
        citation_task, novelty_task, return_exceptions=True
    )

    merged_state = {}
    if isinstance(citation_result, Exception):
        logger.error(f"Citation failed in parallel execution: {citation_result}")
        # Citation failure is NOT fatal — use fallback
        merged_state.update({
            "citations": [],
            "in_text_map": {},
            "writer_citation_status": "Citation Review Required",
        })
    else:
        merged_state.update(citation_result)

    if isinstance(novelty_result, Exception):
        logger.error(f"Novelty failed in parallel execution: {novelty_result}")
        # Novelty failure is never fatal
        merged_state.update({
            "novelty_score": 0.5,
            "novel_contributions": [],
            "research_gaps": [],
        })
    else:
        merged_state.update(novelty_result)

    # Route to writer next
    merged_state["current_agent"] = "citation_novelty"
    return merged_state


def build_research_graph() -> StateGraph:
    """Build the LangGraph research pipeline — fully sequential, no race conditions."""

    graph = StateGraph(ResearchState)

    # ── Add nodes ────────────────────────────────────────
    graph.add_node("planner", planner_node)
    graph.add_node("search", search_node)
    graph.add_node("firecrawl_extract", firecrawl_extract_node)
    graph.add_node("reader", reader_node)
    graph.add_node("claim_extractor", claim_extractor_node)
    graph.add_node("critic", critic_node)
    graph.add_node("citation_novelty", _citation_novelty_parallel_executor)
    graph.add_node("writer", writer_node)
    graph.add_node("critic_paper", critic_paper_node)
    graph.add_node("writer_revision", writer_revision_node)
    graph.add_node("ieee_formatter", ieee_formatter_node)
    graph.add_node("humanizer", humanizer_node)
    graph.add_node("page_validator", page_validation_node)

    # ── Entry point ──────────────────────────────────────
    graph.add_edge(START, "planner")

    # ── All nodes route via should_continue ──────────────
    graph.add_conditional_edges("planner", should_continue)
    graph.add_conditional_edges("search", should_continue)
    graph.add_conditional_edges("firecrawl_extract", should_continue)
    graph.add_conditional_edges("reader", should_continue)
    graph.add_conditional_edges("claim_extractor", should_continue)
    graph.add_conditional_edges("critic", should_continue)
    graph.add_conditional_edges("citation_novelty", should_continue)
    graph.add_conditional_edges("writer", should_continue)
    graph.add_conditional_edges("critic_paper", should_continue)
    graph.add_conditional_edges("writer_revision", should_continue)
    graph.add_conditional_edges("ieee_formatter", should_continue)
    graph.add_conditional_edges("humanizer", should_continue)
    graph.add_conditional_edges("page_validator", should_continue)

    return graph


# Compiled workflow
_compiled_graph = None


def get_research_workflow():
    """Get the compiled research workflow."""
    global _compiled_graph
    if _compiled_graph is None:
        graph = build_research_graph()
        _compiled_graph = graph.compile()
        logger.info("research_workflow_compiled")
    return _compiled_graph
