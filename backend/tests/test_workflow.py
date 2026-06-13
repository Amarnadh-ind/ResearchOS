import sys
import os
import pytest

# Ensure backend directory is in the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from graph.workflow import should_continue, page_validation_router
from graph.state import ResearchState

def test_should_continue():
    # Test failed state halts
    state_failed = {"status": "failed", "current_agent": "planner"}
    assert should_continue(state_failed) == "__end__"

    # Test mapping
    state_search = {"status": "searching", "current_agent": "search"}
    assert should_continue(state_search) == "search"

    state_browser = {"status": "browsing", "current_agent": "browser"}
    assert should_continue(state_browser) == "browser"

    state_done = {"status": "completed", "current_agent": "done"}
    assert should_continue(state_done) == "__end__"

def test_page_validation_router():
    # Test failed halts
    state_failed = {"status": "failed", "current_agent": "page_validator"}
    assert page_validation_router(state_failed) == "__end__"

    # Test loop back for expansion
    state_loop = {"status": "validating_pages", "current_agent": "page_validator"}
    assert page_validation_router(state_loop) == "page_validator"

    # Test completed halts
    state_completed = {"status": "completed", "current_agent": "done"}
    assert page_validation_router(state_completed) == "__end__"
