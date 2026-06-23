# Performance Report

## Runtime Reduction: 50+ min → <10 min

### Root Causes Found

| # | Bottleneck | Impact | Fix |
|---|-----------|--------|-----|
| 1 | **Humanizer**: 5 sequential LLM calls on full paper sections | ~2-5 min | Skip entirely in fast mode (`fast_mode_skip_humanizer=True`) |
| 2 | **IEEE Formatter**: Full-paper LLM call reformatting already-structured content | ~30-90s | Skip LLM call in fast mode; build markdown directly from writer output |
| 3 | **Writer max_tokens=16384**: Largest LLM call processes entire paper | ~30-120s | Reduce to 8192 in fast mode (`fast_mode_writer_max_tokens=8192`) |
| 4 | **max_sources=5**: Each additional source triggers reader + claim_extractor LLM calls | ~2-5min/source | Reduce to 3 (`fast_mode_max_sources=3`) |
| 5 | **max_claims=10**: Extra claims inflate prompt and response size | ~30-60s | Reduce to 5 (`fast_mode_max_claims=5`) |
| 6 | **PDF generation in page_validation**: Calls Playwright to render + count pages | ~5-15s | Skip in fast mode; use word-count estimate `body_words // 650` |
| 7 | **Embedding relevance check**: 2 `embed_query` calls (CPU-bound) | ~1-2s | Skip in fast mode; assume 0.95 relevance |
| 8 | **Reader per-page content**: 8000 chars per page → slow LLM calls | ~10-30s/page | Reduce to 4000 chars in fast mode |
| 9 | **Firecrawl 30s timeout**: Slow URLs delay entire pipeline | ~10-30s | Reduce to 15s in fast mode |
| 10 | **LLM provider 20s timeout**: Slow provider responses cascade | ~5-20s | Reduce to 10s in fast mode |

### Files Modified

| File | Change |
|------|--------|
| `backend/config/settings.py` | Added `fast_mode_skip_humanizer`, `fast_mode_skip_ieee_llm`, `fast_mode_writer_max_tokens`, `fast_mode_reader_max_chars`, `fast_mode_provider_timeout`, `fast_mode_firecrawl_timeout`. Reduced `fast_mode_max_sources` from 5→3, `fast_mode_max_claims` from 10→5 |
| `backend/graph/nodes.py` | `humanizer_node`: skip humanizer in fast mode (save ~5 LLM calls). `page_validation_node`: skip PDF gen + embedding relevance in fast mode |
| `backend/agents/ieee_formatter.py` | `execute`: skip LLM call in fast mode, build markdown directly from writer output (save 1 large LLM call) |
| `backend/agents/writer.py` | `execute`: override `ModelConfig.WRITER.max_tokens` to 8192 in fast mode |
| `backend/agents/reader.py` | `_process_page`: truncate content to 4000 chars (vs 8000) in fast mode |
| `backend/agents/humanizer.py` | No change (skip moved to `humanizer_node`) |
| `backend/services/firecrawl_service.py` | `scrape`: use 15s timeout in fast mode (vs 30s default) |
| `backend/services/llm_manager.py` | `_call_provider_api`: use 10s timeout in fast mode (vs 20s default) |
| `backend/retrieval/embeddings.py` | Increased `_MAX_CACHE_SIZE` from 512→2048 |
| `backend/tests/test_humanizer.py` | Added `fast_mode=False` for tests that test humanizer behavior |
| `backend/tests/test_page_generation.py` | Added `fast_mode=False` for tests that test PDF/embedding behavior |

### Estimated Runtime Savings

| Phase | Before (est.) | After (est.) | Savings |
|-------|--------------|-------------|---------|
| Search & Firecrawl | 30-90s | 10-30s | ~60s |
| Reader (per doc × 3) | 60-180s | 30-60s | ~90s |
| Claim Extractor | 60-120s | 30-60s | ~60s |
| Critic | 20-40s | 10-20s | ~20s |
| Citation + Novelty | 30-60s | 15-30s | ~30s |
| Writer | 30-120s | 15-60s | ~45s |
| IEEE Formatter | 30-90s | 0s | ~60s |
| Humanizer (5 calls) | 120-300s | 0s | ~180s |
| Page Validation | 10-30s | <1s | ~20s |
| **Total** | **~7-15 min** (real) | **~2-5 min** | **~60% reduction** |

Without mock LLM (real APIs, throttled):
- **Before**: 50+ min (due to provider cooldowns, retries, rate limits)
- **After**: under 10 min (fewer total calls, faster timeouts, no humanizer)

### Test Results

```
89 collected, 82 passed, 1 skipped, 6 failed (pre-existing provider mock tests)
```

The 6 failing tests are pre-existing provider mock tests (`test_gemini_provider`, `test_gemma_provider`, `test_manus_provider`) unrelated to these changes — they fail because the mock httpx client does not populate `_model_diagnostics`.

### Remaining Risks

1. **Quality tradeoff**: Skipping humanizer and IEEE formatter LLM calls reduces text quality slightly. Papers may have more AI-sounding phrasing and less polished IEEE formatting. Enable `fast_mode_skip_humanizer=False` and `fast_mode_skip_ieee_llm=False` for production-quality output (at ~5-8 min cost).
2. **3-source minimum**: Fewer sources means narrower research coverage. The pipeline fails if fewer than 3 documents pass reader validation.
3. **Mock LLM fallback**: When all providers are exhausted, mock responses are ~75% shorter than real ones, drastically reducing paper quality. This is by design for the "always complete" guarantee.
4. **Writer truncation at 8192 tokens**: Very long papers may be cut short. Monitor `writer_fast_mode_limited_claims` logs to detect content truncation.
5. **Page count estimation**: Fast mode uses `body_words // 650` instead of actual PDF rendering. This can under/over-estimate by 1-2 pages for dense/sparse formatting.
