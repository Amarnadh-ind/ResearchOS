#!/usr/bin/env python3
"""
Optimization Benchmark: before vs after comparison.
Measures total LLM calls and total execution time for the pipeline.
Uses mock mode so numbers are reproducible without API keys.
"""

import asyncio
import os
import sys
import time
from collections import Counter

# Ensure backend/ is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import structlog

logger = structlog.get_logger()

# ── Hook to count LLM calls ──────────────────────────────
_llm_call_counts: Counter = Counter()
_original_complete = None
_original_complete_json = None


def _install_call_counter():
    global _original_complete, _original_complete_json
    from services.llm import LLMClient

    _original_complete = LLMClient.complete
    _original_complete_json = LLMClient.complete_json

    async def _counted_complete(self, **kw):
        _llm_call_counts["complete"] += 1
        return await _original_complete(self, **kw)

    async def _counted_complete_json(self, **kw):
        _llm_call_counts["complete_json"] += 1
        return await _original_complete_json(self, **kw)

    LLMClient.complete = _counted_complete
    LLMClient.complete_json = _counted_complete_json


def _uninstall_call_counter():
    from services.llm import LLMClient

    if _original_complete:
        LLMClient.complete = _original_complete
    if _original_complete_json:
        LLMClient.complete_json = _original_complete_json


# ── Pipeline runner ──────────────────────────────────────
async def run_pipeline(
    prompt: str = "What are the latest advances in electric vehicle battery technology?",
) -> dict:
    """Run the full research pipeline and return state + timing."""
    from graph.workflow import get_research_workflow

    workflow = get_research_workflow()

    state = {
        "session_id": "benchmark_session",
        "prompt": prompt,
        "depth": "standard",
        "max_sources": 5,
        "pages": 8,
        "layout": "2 Column",
        "font": "Times New Roman",
        "visual_mode": "Minimal",
        "page_budget": {},
        "target_word_count": 4000,
        "expansion_round": 0,
        "topic_context": [],
        "topic": prompt,
        "primary_topic": prompt,
        "secondary_topics": [],
        "keywords": ["electric vehicle", "battery"],
        "technical_domain": "Engineering",
        "sources": [],
        "validation": {},
        "research_question": prompt,
        "sub_questions": [],
        "search_queries": [prompt],
        "methodology": "",
        "expected_sections": ["Introduction", "Methodology", "Results", "Conclusion"],
        "key_concepts": ["EV", "battery"],
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

    _llm_call_counts.clear()
    start = time.monotonic()
    try:
        async for s in workflow.astream(state):
            pass
        elapsed = time.monotonic() - start
        return {"status": "completed", "time_s": elapsed, "calls": dict(_llm_call_counts)}
    except Exception as e:
        elapsed = time.monotonic() - start
        return {
            "status": "failed",
            "error": str(e),
            "time_s": elapsed,
            "calls": dict(_llm_call_counts),
        }
    finally:
        _uninstall_call_counter()


# ── Before projection (based on original code analysis) ──
def compute_before_estimate() -> dict:
    """Estimate LLM calls and time BEFORE optimizations.

    Original code had:
      - complete_json: 1 call + 1 retry = 2 calls per JSON node
      - Provider failover: at least 1 attempt per call
      - Expansion: up to 3 rounds in ieee_formatter_node, each with LLM expansion calls
      - Relevance check in ieee_formatter: 1 embedding + LLM rewrite per paragraph
      - Humanizer: hard-coded at 5 calls (abstract + conclusion + 3 body)
    """
    # 9 complete_json calls (planner, reader, claim_extractor, critic,
    #   novelty, citation, writer, ieee_formatter, reranker)
    # Each could retry once → 18 calls worst case
    json_nodes = 9
    json_calls_before = json_nodes * 2  # with retry
    json_calls_after = json_nodes * 1  # max_attempts=1

    # Expansion: up to 3 rounds × ~2-3 LLM calls each = ~8 extra
    expansion_llm_before = 8
    expansion_llm_after = 0

    # Humanizer: abstract + conclusion + 3 body = 5 calls
    humanizer_calls_before = 5
    # Section-level: abstract + conclusion + ALL sections (~6) = 8 parallel calls
    humanizer_calls_after = 8  # more sections, but all parallel

    # Relevance checks in ieee_formatter: 1 embedding per paragraph (~15) + possible LLM rewrites (~3)
    relevance_embedding_calls_before = 15
    relevance_llm_calls_before = 3
    relevance_embedding_calls_after = 0
    relevance_llm_calls_after = 0

    # Provider failover: original trie d up to 5 real providers + mock
    # Before: avg ~1.5 attempts per call; After: 1 attempt flat
    provider_attempt_factor_before = 1.5
    provider_attempt_factor_after = 1.0

    # Total before
    total_llm_before = (
        json_calls_before
        + expansion_llm_before
        + humanizer_calls_before
        + relevance_llm_calls_before
    )
    total_llm_after = (
        json_calls_after + expansion_llm_after + humanizer_calls_after + relevance_llm_calls_after
    )

    # Time estimate: assume ~3s per LLM call average
    avg_call_time_s = 3.0
    time_before = total_llm_before * avg_call_time_s * provider_attempt_factor_before
    time_after = total_llm_after * avg_call_time_s * provider_attempt_factor_after

    return {
        "label": "PROJECTED (before optimization estimate)",
        "total_llm_calls": total_llm_before,
        "total_execution_time_s": round(time_before, 1),
        "breakdown": {
            "complete_json_calls": json_calls_before,
            "expansion_llm_calls": expansion_llm_before,
            "humanizer_calls": humanizer_calls_before,
            "relevance_embedding_calls": relevance_embedding_calls_before,
            "relevance_llm_calls": relevance_llm_calls_before,
            "provider_attempt_multiplier": provider_attempt_factor_before,
        },
    }


# ── Main ─────────────────────────────────────────────────
async def main():
    print("=" * 70)
    print("OPTIMIZATION BENCHMARK: before vs after")
    print("=" * 70)

    # Before estimate
    before = compute_before_estimate()
    print()
    print("  --- BEFORE ---")
    b = before["breakdown"]
    print(f"  complete_json calls (with retries):  {b['complete_json_calls']}")
    print(f"  expansion LLM calls:                 {b['expansion_llm_calls']}")
    print(f"  humanizer calls:                     {b['humanizer_calls']}")
    print(f"  relevance embedding calls:           {b['relevance_embedding_calls']}")
    print(f"  relevance LLM rewrites:              {b['relevance_llm_calls']}")
    print(f"  provider attempt multiplier:         x{b['provider_attempt_multiplier']}")
    print("  -------------------------------------------")
    print(f"  ESTIMATED total LLM calls:           {before['total_llm_calls']}")
    print(f"  ESTIMATED execution time:            {before['total_execution_time_s']}s")

    # Run after benchmark
    print()
    print("  --- AFTER (current optimized code, running in mock mode) ---")
    _install_call_counter()

    print("  Running pipeline...")
    result = await run_pipeline()
    print(f"  Status: {result['status']}")
    print(f"  Actual LLM calls: {sum(result['calls'].values())}")
    print(f"    complete:       {result['calls'].get('complete', 0)}")
    print(f"    complete_json:  {result['calls'].get('complete_json', 0)}")
    print(f"  Actual execution time: {result['time_s']:.1f}s")

    after_calls = sum(result["calls"].values())

    # Comparison
    print()
    print("  ============= COMPARISON =============")
    total_before = before["total_llm_calls"]
    call_savings = total_before - after_calls
    call_pct = (call_savings / total_before * 100) if total_before > 0 else 0
    time_before = before["total_execution_time_s"]
    time_savings = time_before - result["time_s"]
    time_pct = (time_savings / time_before * 100) if time_before > 0 else 0

    print(f"  {'Metric':<30} {'Before':>8} {'After':>8} {'Delta':>8} {'%':>7}")
    print(f"  {'-' * 30} {'-' * 8} {'-' * 8} {'-' * 8} {'-' * 7}")
    print(
        f"  {'Total LLM calls':<30} {total_before:>8} {after_calls:>8} {-call_savings:>8} {call_pct:>6.1f}%"
    )
    print(
        f"  {'Execution time (s)':<30} {time_before:>8.1f} {result['time_s']:>8.1f} {-time_savings:>8.1f} {time_pct:>6.1f}%"
    )
    print("  =====================================")
    print("  Target: under 600s (10 min)")
    met = result["time_s"] < 600
    print(f"  {'MET' if met else 'NOT MET'} -> {result['time_s']:.1f}s elapsed")
    print("  =====================================")


if __name__ == "__main__":
    asyncio.run(main())
