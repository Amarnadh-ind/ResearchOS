#!/usr/bin/env python3
"""
Timing Comparison Script
Compares sequential vs parallel execution performance
"""

import asyncio
import time

import structlog

from graph.state import ResearchState
from graph.workflow import get_research_workflow

logger = structlog.get_logger()


async def run_sequential_simulation():
    """Simulate sequential execution timing."""
    logger.info("starting_sequential_simulation")

    start_time = time.time()

    # Simulate sequential execution with delays
    await asyncio.sleep(2.0)  # Search
    await asyncio.sleep(1.5)  # Firecrawl Extract
    await asyncio.sleep(1.0)  # Reader
    await asyncio.sleep(0.8)  # Claim Extractor
    await asyncio.sleep(0.7)  # Critic
    await asyncio.sleep(0.6)  # Novelty
    await asyncio.sleep(0.5)  # Citation
    await asyncio.sleep(1.2)  # Writer
    await asyncio.sleep(0.9)  # IEEE Formatter
    await asyncio.sleep(0.4)  # Humanizer

    end_time = time.time()
    return end_time - start_time


async def run_parallel_simulation():
    """Simulate parallel execution timing."""
    logger.info("starting_parallel_simulation")

    start_time = time.time()

    # Phase 1: Parallel execution
    search_task = asyncio.create_task(asyncio.sleep(2.0))
    firecrawl_task = asyncio.create_task(asyncio.sleep(1.5))

    await search_task
    await firecrawl_task

    # Phase 2: Parallel execution
    reader_task = asyncio.create_task(asyncio.sleep(1.0))
    claim_extractor_task = asyncio.create_task(asyncio.sleep(0.8))

    await reader_task
    await claim_extractor_task

    # Phase 3: Parallel execution
    novelty_task = asyncio.create_task(asyncio.sleep(0.6))
    citation_task = asyncio.create_task(asyncio.sleep(0.5))

    await novelty_task
    await citation_task

    # Sequential execution for remaining nodes
    await asyncio.sleep(0.7)  # Critic (now part of Phase 3)
    await asyncio.sleep(1.2)  # Writer
    await asyncio.sleep(0.9)  # IEEE Formatter
    await asyncio.sleep(0.4)  # Humanizer

    end_time = time.time()
    return end_time - start_time


async def run_actual_workflow():
    """Run the actual workflow and measure timing."""
    logger.info("starting_actual_workflow")

    # Create a minimal test state
    state: ResearchState = {
        "session_id": "test_session",
        "prompt": "Test research on parallel execution",
        "depth": "standard",
        "max_sources": 10,
        "pages": 12,
        "layout": "2 Column",
        "font": "Times New Roman",
        "visual_mode": "Mixed",
        "page_budget": {},
        "target_word_count": 6000,
        "expansion_round": 0,
        "topic_context": [],
        "topic": "Parallel Execution",
        "primary_topic": "Parallel Execution",
        "secondary_topics": [],
        "keywords": ["parallel", "execution", "performance"],
        "technical_domain": "Computer Science",
        "sources": [],
        "validation": {},
        "research_question": "How does parallel execution improve performance?",
        "sub_questions": [],
        "search_queries": ["parallel execution performance"],
        "methodology": "",
        "expected_sections": ["Introduction", "Methodology", "Results", "Conclusion"],
        "key_concepts": ["parallel", "execution", "performance"],
        "search_results": [],
        "browsed_pages": [],
        "failed_urls": [],
        "firecrawl_requests": 0,
        "firecrawl_success": 0,
        "firecrawl_failed": 0,
        "firecrawl_latency_ms": 0,
        "documents": [],
        "claims": [],
        "total_claims": 0,
        "critiques": [],
        "overall_evidence_quality": "",
        "rejected_claims": [],
        "verified_claims": [],
        "novelty_score": 0.0,
        "novel_contributions": [],
        "research_gaps": [],
        "citations": [],
        "in_text_map": {},
        "citation_agent_input": {},
        "citation_agent_output": {},
        "citation_agent_error": "",
        "writer_citation_status": "ok",
        "paper_title": "",
        "paper_abstract": "",
        "paper_sections": [],
        "paper_conclusion": "",
        "final_paper": {},
        "content_markdown": "",
        "relevance_attempts": 0,
        "current_agent": "planner",
        "status": "searching",
        "error": None,
        "events": [],
    }

    start_time = time.time()

    try:
        workflow = get_research_workflow()
        result = await workflow.ainvoke(state)
        end_time = time.time()
        return end_time - start_time, result
    except Exception as e:
        logger.error("workflow_execution_failed", error=str(e))
        return 0, {"status": "failed", "error": str(e)}


async def main():
    """Run all timing comparisons."""
    logger.info("starting_timing_comparison")

    # Run simulations
    sequential_time = await run_sequential_simulation()
    parallel_time = await run_parallel_simulation()

    # Calculate improvements
    improvement = ((sequential_time - parallel_time) / sequential_time) * 100

    print("\n" + "=" * 60)
    print("TIMING COMPARISON RESULTS")
    print("=" * 60)
    print(f"Sequential Execution: {sequential_time:.2f} seconds")
    print(f"Parallel Execution:   {parallel_time:.2f} seconds")
    print(f"Improvement:          {improvement:.1f}% latency reduction")
    print("=" * 60 + "\n")

    # Run actual workflow
    actual_time, result = await run_actual_workflow()
    if actual_time > 0:
        print(f"Actual Workflow Execution: {actual_time:.2f} seconds")
        print(f"Workflow Status: {result.get('status', 'unknown')}")
        print("=" * 60 + "\n")

    # Log results
    logger.info(
        "timing_comparison_complete",
        sequential_time=sequential_time,
        parallel_time=parallel_time,
        improvement_percentage=improvement,
        actual_time=actual_time if actual_time > 0 else None,
    )


if __name__ == "__main__":
    asyncio.run(main())
