"""
LangGraph Research Workflow
Defines the StateGraph for the full research pipeline.

Pipeline:
Prompt → Planner → Search → Browser → Reader → Claim Extractor
→ Critic → Novelty → Citation → Writer → IEEE Formatter
→ Page Validator (loops until page count is met) → Final Paper
"""

import structlog
from langgraph.graph import StateGraph, START, END

from graph.state import ResearchState
from graph.nodes import (
    planner_node,
    search_node,
    browser_node,
    reader_node,
    claim_extractor_node,
    critic_node,
    novelty_node,
    citation_node,
    writer_node,
    ieee_formatter_node,
    page_validation_node,
    humanizer_node,
)

logger = structlog.get_logger()


def should_continue(state: ResearchState) -> str:
    """Route based on pipeline status. Stops on failure."""
    status = state.get("status", "")
    if status == "failed":
        return END

    agent = state.get("current_agent", "")
    route_map = {
        "search": "search",
        "browser": "browser",
        "reader": "reader",
        "claim_extractor": "claim_extractor",
        "critic": "critic",
        "novelty": "novelty",
        "citation": "citation",
        "writer": "writer",
        "ieee_formatter": "ieee_formatter",
        "humanizer": "humanizer",
        "page_validator": "page_validator",
        "done": END,
    }
    return route_map.get(agent, END)


def page_validation_router(state: ResearchState) -> str:
    """Route after page validation: loop back if pages short, else finish."""
    status = state.get("status", "")
    if status == "failed":
        return END
    if status == "completed":
        return END

    agent = state.get("current_agent", "")
    if agent == "page_validator":
        # Loop back to self for expansion
        return "page_validator"
    if agent == "writer":
        return "writer"
    if agent == "done":
        return END

    return END


def build_research_graph() -> StateGraph:
    """Build the LangGraph research pipeline with page validation loop."""

    graph = StateGraph(ResearchState)

    # ── Add nodes ────────────────────────────────────────
    graph.add_node("planner", planner_node)
    graph.add_node("search", search_node)
    graph.add_node("browser", browser_node)
    graph.add_node("reader", reader_node)
    graph.add_node("claim_extractor", claim_extractor_node)
    graph.add_node("critic", critic_node)
    graph.add_node("novelty", novelty_node)
    graph.add_node("citation", citation_node)
    graph.add_node("writer", writer_node)
    graph.add_node("ieee_formatter", ieee_formatter_node)
    graph.add_node("humanizer", humanizer_node)
    graph.add_node("page_validator", page_validation_node)

    # ── Entry point ──────────────────────────────────────
    graph.add_edge(START, "planner")

    # ── Conditional routing after each node ──────────────
    graph.add_conditional_edges("planner", should_continue)
    graph.add_conditional_edges("search", should_continue)
    graph.add_conditional_edges("browser", should_continue)
    graph.add_conditional_edges("reader", should_continue)
    graph.add_conditional_edges("claim_extractor", should_continue)
    graph.add_conditional_edges("critic", should_continue)
    graph.add_conditional_edges("novelty", should_continue)
    graph.add_conditional_edges("citation", should_continue)
    graph.add_conditional_edges("writer", should_continue)
    graph.add_conditional_edges("ieee_formatter", should_continue)
    graph.add_conditional_edges("humanizer", should_continue)

    # Page validator can loop back to itself or finish
    graph.add_conditional_edges("page_validator", page_validation_router)

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
