import os
import sys

# Ensure backend directory is in the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from graph.workflow import should_continue


def test_should_continue():
    # Test failed state halts
    state_failed = {"status": "failed", "current_agent": "planner"}
    assert should_continue(state_failed) == "__end__"

    # Sequential pipeline routing asserts
    state_planner = {"status": "planning", "current_agent": "planner"}
    assert should_continue(state_planner) == "search"

    state_search = {"status": "searching", "current_agent": "search"}
    assert should_continue(state_search) == "firecrawl_extract"

    state_firecrawl = {"status": "browsing", "current_agent": "firecrawl_extract"}
    assert should_continue(state_firecrawl) == "reader"

    state_reader = {"status": "reading", "current_agent": "reader"}
    assert should_continue(state_reader) == "claim_extractor"

    state_claim = {"status": "extracting", "current_agent": "claim_extractor"}
    assert should_continue(state_claim) == "critic"

    state_critic = {"status": "critiquing", "current_agent": "critic"}
    assert should_continue(state_critic) == "citation_novelty"

    state_parallel_citation = {"status": "citing", "current_agent": "citation_novelty"}
    assert should_continue(state_parallel_citation) == "writer"

    # Test sequential pipeline routing
    state_writer = {"status": "writing", "current_agent": "writer"}
    assert should_continue(state_writer) == "critic_paper"

    state_critic_paper = {"status": "revising", "current_agent": "critic_paper"}
    assert should_continue(state_critic_paper) == "writer_revision"

    state_writer_revision = {"status": "formatting", "current_agent": "writer_revision"}
    assert should_continue(state_writer_revision) == "ieee_formatter"

    state_ieee = {"status": "humanizing", "current_agent": "ieee_formatter"}
    assert should_continue(state_ieee) == "humanizer"

    state_humanizer = {"status": "validating_pages", "current_agent": "humanizer"}
    assert should_continue(state_humanizer) == "page_validator"

    state_validator = {"status": "done", "current_agent": "page_validator"}
    assert should_continue(state_validator) == "done"

    # Test terminal
    state_done = {"status": "completed", "current_agent": "done"}
    assert should_continue(state_done) == "__end__"
