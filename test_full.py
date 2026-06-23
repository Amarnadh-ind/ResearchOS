import asyncio
import time
import sys
sys.path.insert(0, r'D:\research os\backend')

from graph.nodes import (
    planner_node, search_node, firecrawl_extract_node,
    reader_node, claim_extractor_node, critic_node,
    citation_node, novelty_node, writer_node,
    critic_paper_node, writer_revision_node,
    ieee_formatter_node, humanizer_node, page_validation_node
)

async def run_pipeline():
    # Initial state
    state = {
        "prompt": "Write a research paper on transformer architectures",
        "depth": "standard",
        "max_sources": 5,
        "pages": 4,
        "layout": "2 Column",
        "font": "Times New Roman",
        "visual_mode": "Mixed",
        "page_budget": {},
        "target_word_count": 0,
        "expansion_round": 0,
        "status": "planning",
        "current_agent": "planner",
        "events": [],
        "topic_context": [],
    }
    
    timings = {}
    start_total = time.monotonic()
    
    # Planner
    t0 = time.monotonic()
    result = await planner_node(state)
    timings['planner'] = time.monotonic() - t0
    print(f"Planner: {timings['planner']:.1f}s")
    state.update(result)
    
    # Search (sequential)
    t0 = time.monotonic()
    result = await search_node(state)
    timings['search'] = time.monotonic() - t0
    print(f"Search: {timings['search']:.1f}s")
    state.update(result)
    
    # Firecrawl (after search)
    t0 = time.monotonic()
    result = await firecrawl_extract_node(state)
    timings['firecrawl'] = time.monotonic() - t0
    print(f"Firecrawl: {timings['firecrawl']:.1f}s")
    state.update(result)
    
    # Reader
    t0 = time.monotonic()
    result = await reader_node(state)
    timings['reader'] = time.monotonic() - t0
    print(f"Reader: {timings['reader']:.1f}s")
    state.update(result)
    
    # Claims
    t0 = time.monotonic()
    result = await claim_extractor_node(state)
    timings['claims'] = time.monotonic() - t0
    print(f"Claims: {timings['claims']:.1f}s")
    state.update(result)
    
    # Critic
    t0 = time.monotonic()
    result = await critic_node(state)
    timings['critic'] = time.monotonic() - t0
    print(f"Critic: {timings['critic']:.1f}s")
    state.update(result)
    
    # Citation
    t0 = time.monotonic()
    result = await citation_node(state)
    timings['citation'] = time.monotonic() - t0
    print(f"Citation: {timings['citation']:.1f}s")
    state.update(result)
    
    # Novelty
    t0 = time.monotonic()
    result = await novelty_node(state)
    timings['novelty'] = time.monotonic() - t0
    print(f"Novelty: {timings['novelty']:.1f}s")
    state.update(result)
    
    # Writer
    t0 = time.monotonic()
    result = await writer_node(state)
    timings['writer'] = time.monotonic() - t0
    print(f"Writer: {timings['writer']:.1f}s")
    state.update(result)
    
    # Critic Paper
    t0 = time.monotonic()
    result = await critic_paper_node(state)
    timings['critic_paper'] = time.monotonic() - t0
    print(f"Critic Paper: {timings['critic_paper']:.1f}s")
    state.update(result)
    
    # Writer Revision
    t0 = time.monotonic()
    result = await writer_revision_node(state)
    timings['writer_revision'] = time.monotonic() - t0
    print(f"Writer Revision: {timings['writer_revision']:.1f}s")
    state.update(result)
    
    # IEEE Formatter
    t0 = time.monotonic()
    result = await ieee_formatter_node(state)
    timings['ieee'] = time.monotonic() - t0
    print(f"IEEE Formatter: {timings['ieee']:.1f}s")
    state.update(result)
    
    # Humanizer
    t0 = time.monotonic()
    result = await humanizer_node(state)
    timings['humanizer'] = time.monotonic() - t0
    print(f"Humanizer: {timings['humanizer']:.1f}s")
    state.update(result)
    
    # Page Validator
    t0 = time.monotonic()
    result = await page_validation_node(state)
    timings['validator'] = time.monotonic() - t0
    print(f"Page Validator: {timings['validator']:.1f}s")
    state.update(result)
    
    total = time.monotonic() - start_total
    print(f"\n=== TOTAL: {total:.1f}s ===")
    for k, v in timings.items():
        pct = v / total * 100
        print(f"  {k:20s}: {v:6.1f}s ({pct:5.1f}%)")

asyncio.run(run_pipeline())
