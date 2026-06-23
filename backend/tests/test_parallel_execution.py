#!/usr/bin/env python3
"""
Test Script for Sequential Workflow and Citation/Novelty Parallel Execution
Validates the sequential workflow and the parallel execution of citation & novelty nodes.
"""

import asyncio
import os
import sys

import pytest

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from graph.workflow import (
    _citation_novelty_parallel_executor,
    build_research_graph,
)


def test_parallel_executor_functions_exist():
    """Test that parallel executor functions exist and are callable."""
    print("Testing parallel executor functions...")
    
    # Check that functions exist
    assert callable(_citation_novelty_parallel_executor), "citation_novelty parallel executor not callable"
    
    print("OK All parallel executor functions exist and are callable")


def test_workflow_builds():
    """Test that the workflow builds successfully."""
    print("Testing workflow build...")
    
    try:
        graph = build_research_graph()
        assert graph is not None, "Graph is None"
        assert hasattr(graph, 'compile'), "Graph has no compile method"
        
        print("OK Workflow builds successfully")
    except Exception as e:
        print(f"FAIL Workflow build failed: {e}")
        raise


def test_workflow_nodes():
    """Test that workflow nodes are properly configured."""
    print("Testing workflow nodes...")
    
    graph = build_research_graph()
    
    expected_nodes = [
        "planner",
        "search",
        "firecrawl_extract",
        "reader",
        "claim_extractor",
        "critic",
        "citation_novelty",
        "writer",
        "critic_paper",
        "writer_revision",
        "ieee_formatter",
        "humanizer",
        "page_validator"
    ]
    
    for node in expected_nodes:
        assert node in graph.nodes, f"Node '{node}' not found in graph"
    
    print("OK All expected workflow nodes are present")


def test_routing_logic():
    """Test that routing logic handles sequential agents correctly."""
    print("Testing routing logic...")
    
    from graph.workflow import should_continue
    
    test_cases = [
        # Sequential pipeline routing
        ({"current_agent": "planner", "status": "planning"}, "search"),
        ({"current_agent": "search", "status": "searching"}, "firecrawl_extract"),
        ({"current_agent": "firecrawl_extract", "status": "browsing"}, "reader"),
        ({"current_agent": "reader", "status": "reading"}, "claim_extractor"),
        ({"current_agent": "claim_extractor", "status": "extracting"}, "critic"),
        ({"current_agent": "critic", "status": "critiquing"}, "citation_novelty"),
        ({"current_agent": "citation_novelty", "status": "citing"}, "writer"),
        ({"current_agent": "writer", "status": "writing"}, "critic_paper"),
        ({"current_agent": "critic_paper", "status": "revising"}, "writer_revision"),
        ({"current_agent": "writer_revision", "status": "formatting"}, "ieee_formatter"),
        ({"current_agent": "ieee_formatter", "status": "formatting"}, "humanizer"),
        ({"current_agent": "humanizer", "status": "humanizing"}, "page_validator"),
        ({"current_agent": "page_validator", "status": "validating_pages"}, "done"),

        # Terminal
        ({"current_agent": "done", "status": "completed"}, "__end__"),
    ]
    
    for state, expected in test_cases:
        result = should_continue(state)
        assert result == expected, f"Expected {expected}, got {result} for {state}"
    
    print("OK All routing logic tests passed")


def test_parallel_executor_signatures():
    """Test that parallel executor functions have correct signatures."""
    print("Testing parallel executor signatures...")
    
    import inspect
    
    sig = inspect.signature(_citation_novelty_parallel_executor)
    assert len(sig.parameters) == 1, "citation_novelty executor should accept 1 parameter"
    assert "state" in sig.parameters, "citation_novelty executor should have 'state' parameter"
    
    print("OK All parallel executor signatures are correct")


@pytest.mark.asyncio
async def test_async_functions():
    """Test that async functions are properly defined."""
    print("Testing async functions...")
    
    # Check that functions are async
    assert asyncio.iscoroutinefunction(_citation_novelty_parallel_executor), "citation_novelty executor should be async"
    
    print("OK All parallel executor functions are async")


def main():
    """Run all tests."""
    print("="*60)
    print("SEQUENTIAL WORKFLOW TEST SUITE")
    print("="*60)
    
    try:
        test_parallel_executor_functions_exist()
        test_workflow_builds()
        test_workflow_nodes()
        test_routing_logic()
        test_parallel_executor_signatures()
        
        # Run async tests
        asyncio.run(test_async_functions())
        
        print("\n" + "="*60)
        print("ALL TESTS PASSED")
        print("="*60)
        
        return 0
        
    except Exception as e:
        print(f"\nFAIL TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
