"""
FAST_MODE Benchmark
Compares LLM call counts, Firecrawl requests, and estimated latency
between NORMAL mode and FAST_MODE.
"""

import asyncio

# ── Configurable timing constants (milliseconds per LLM call type) ──
JSON_SMALL_MS = 5000  # Planner, Critic, Novelty, Citation
JSON_MEDIUM_MS = 8000  # Reader, ClaimExtractor
JSON_LARGE_MS = 12000  # Writer, IEEEFormatter main
COMPLETE_SMALL_MS = 2000  # Humanizer section, relevance rewrites, revision
FIRECRAWL_PER_URL_MS = 6000
FIRECRAWL_BATCH_OVERHEAD_MS = 10000
EMBEDDING_MS = 100  # Per paragraph embedding


def format_ms(ms: float) -> str:
    if ms >= 60_000:
        return f"{ms / 60_000:.1f}m {ms % 60_000 / 1000:.0f}s"
    return f"{ms / 1000:.1f}s"


class Phase:
    def __init__(self, name: str):
        self.name = name
        self.llm_calls_normal: list[tuple[str, int]] = []  # (type, ms)
        self.llm_calls_fast: list[tuple[str, int]] = []
        self.firecrawl_reqs_normal = 0
        self.firecrawl_reqs_fast = 0
        self.embedding_calls_normal = 0
        self.embedding_calls_fast = 0
        self.notes_normal: list[str] = []
        self.notes_fast: list[str] = []

    def add_json_small(self, count: int, label: str, fast_count: int | None = None):
        self.llm_calls_normal.extend([("json_small", JSON_SMALL_MS)] * count)
        c = fast_count if fast_count is not None else count
        self.llm_calls_fast.extend([("json_small", JSON_SMALL_MS)] * c)

    def add_json_medium(self, count: int, label: str, fast_count: int | None = None):
        self.llm_calls_normal.extend([("json_medium", JSON_MEDIUM_MS)] * count)
        c = fast_count if fast_count is not None else count
        self.llm_calls_fast.extend([("json_medium", JSON_MEDIUM_MS)] * c)

    def add_json_large(self, count: int, label: str, fast_count: int | None = None):
        self.llm_calls_normal.extend([("json_large", JSON_LARGE_MS)] * count)
        c = fast_count if fast_count is not None else count
        self.llm_calls_fast.extend([("json_large", JSON_LARGE_MS)] * c)

    def add_complete_small(self, count: int, label: str, fast_count: int | None = None):
        self.llm_calls_normal.extend([("complete_small", COMPLETE_SMALL_MS)] * count)
        c = fast_count if fast_count is not None else count
        self.llm_calls_fast.extend([("complete_small", COMPLETE_SMALL_MS)] * c)

    def add_firecrawl(self, count: int, fast_count: int | None = None):
        self.firecrawl_reqs_normal = count
        self.firecrawl_reqs_fast = fast_count if fast_count is not None else count

    def add_embeddings(self, count: int, fast_count: int | None = None):
        self.embedding_calls_normal = count
        self.embedding_calls_fast = fast_count if fast_count is not None else count

    def total_llm_ms(self, mode: str) -> int:
        calls = self.llm_calls_normal if mode == "normal" else self.llm_calls_fast
        return sum(ms for _, ms in calls)

    def total_llm_count(self, mode: str) -> int:
        calls = self.llm_calls_normal if mode == "normal" else self.llm_calls_fast
        return len(calls)

    def total_firecrawl_ms(self, mode: str) -> int:
        n = self.firecrawl_reqs_normal if mode == "normal" else self.firecrawl_reqs_fast
        return n * FIRECRAWL_PER_URL_MS + FIRECRAWL_BATCH_OVERHEAD_MS if n > 0 else 0

    def total_embedding_ms(self, mode: str) -> int:
        n = self.embedding_calls_normal if mode == "normal" else self.embedding_calls_fast
        return n * EMBEDDING_MS

    def total_ms(self, mode: str) -> int:
        return (
            self.total_llm_ms(mode) + self.total_firecrawl_ms(mode) + self.total_embedding_ms(mode)
        )

    def summary_line(self, mode: str) -> str:
        llm = self.total_llm_count(mode)
        llm_ms = self.total_llm_ms(mode)
        fc = self.firecrawl_reqs_normal if mode == "normal" else self.firecrawl_reqs_fast
        fc_ms = self.total_firecrawl_ms(mode)
        emb = self.embedding_calls_normal if mode == "normal" else self.embedding_calls_fast
        emb_ms = self.total_embedding_ms(mode)
        total = llm_ms + fc_ms + emb_ms
        notes = self.notes_normal if mode == "normal" else self.notes_fast
        note_str = f"  # {', '.join(notes)}" if notes else ""
        return (
            f"  LLM:{llm:2d} ({format_ms(llm_ms)})  "
            f"Firecrawl:{fc:2d} ({format_ms(fc_ms)})  "
            f"Embed:{emb:3d} ({format_ms(emb_ms)})  "
            f"Total:{format_ms(total)}{note_str}"
        )


def build_phases() -> list[Phase]:
    phases = []

    # ── Planner ──
    p = Phase("Planner")
    p.add_json_small(2, "normalize_topic + plan")
    p.notes_normal.append("2 JSON calls")
    p.notes_fast.append("2 JSON calls (max_attempts=1)")
    phases.append(p)

    # ── Search ──
    p = Phase("Search")
    p.notes_normal.append("0 LLM calls (web API only)")
    p.notes_fast.append("0 LLM calls (web API only)")
    phases.append(p)

    # ── Firecrawl Extract ──
    p = Phase("FirecrawlExtract")
    p.add_firecrawl(15, fast_count=5)
    p.notes_normal.append("15 URLs scraped")
    p.notes_fast.append("5 URLs scraped")
    phases.append(p)

    # ── Reader ──
    p = Phase("Reader")
    p.add_json_medium(10, "pages (N=10)", fast_count=4)
    p.notes_normal.append("~10 pages read")
    p.notes_fast.append("~4 pages read (5 sources, some filtered)")
    phases.append(p)

    # ── Claim Extractor ──
    p = Phase("ClaimExtractor")
    p.add_json_medium(10, "docs (N=10)", fast_count=4)
    p.notes_normal.append("~10 documents processed, 30+ claims")
    p.notes_fast.append("~4 documents, max 10 claims")
    phases.append(p)

    # ── Critic ──
    p = Phase("Critic")
    p.add_json_small(1, "batch critique")
    p.notes_normal.append("1 batched JSON call")
    p.notes_fast.append("1 batched JSON call (max_attempts=1)")
    phases.append(p)

    # ── Novelty ──
    p = Phase("Novelty")
    p.add_json_small(1, "novelty assessment")
    phases.append(p)

    # ── Citation ──
    p = Phase("Citation")
    p.add_json_small(1, "citation generation")
    phases.append(p)

    # ── Writer ──
    p = Phase("Writer")
    p.add_json_large(1, "main draft")
    # Normal: ~3 failed paragraph rewrites
    p.add_complete_small(3, "relevance rewrites", fast_count=0)
    # Normal: ~30 paragraphs with relevance embedding check
    p.add_embeddings(30, fast_count=0)
    p.notes_normal.append("1 JSON + ~3 LLM rewrites + 30 embeddings")
    p.notes_fast.append("1 JSON only (no relevance checks)")
    phases.append(p)

    # ── PaperCritic ──
    p = Phase("PaperCritic")
    p.notes_normal.append("0 LLM calls (structural check)")
    p.notes_fast.append("0 LLM calls")
    phases.append(p)

    # ── WriterRevision ──
    p = Phase("WriterRevision")
    p.add_complete_small(1, "template expansion", fast_count=0)
    p.notes_normal.append("1 LLM call if expansion needed")
    p.notes_fast.append("0 calls (no expansion)")
    phases.append(p)

    # ── IEEEFormatter ──
    p = Phase("IEEEFormatter")
    p.add_json_large(1, "IEEE format")
    # Normal: ~3 failed paragraph rewrites (DUPLICATE of Writer's)
    p.add_complete_small(3, "relevance rewrites", fast_count=0)
    # Normal: ~30 paragraphs re-checked (cached, but embedding lookup still happens)
    p.add_embeddings(0, fast_count=0)  # 0 because embedding cache serves it
    p.notes_normal.append("1 JSON + ~3 LLM rewrites (duplicate, cache helps embeddings)")
    p.notes_fast.append("1 JSON only (no relevance checks)")
    phases.append(p)

    # ── Humanizer ──
    p = Phase("Humanizer")
    p.add_complete_small(5, "section-level humanize")
    p.notes_normal.append("5 section-level LLM calls (already optimized)")
    p.notes_fast.append("5 section-level LLM calls (unchanged)")
    phases.append(p)

    # ── PageValidator ──
    p = Phase("PageValidator")
    p.add_embeddings(2, fast_count=2)
    p.notes_normal.append("0 LLM calls, 2 embeddings (topic relevance)")
    p.notes_fast.append("0 LLM calls, 2 embeddings (unchanged)")
    phases.append(p)

    # ── Expansion loop (IEEE → content_expander, 2 extra rounds) ──
    p = Phase("ExpansionLoop")
    # Normal: 2 extra rounds of revision + ieee + humanizer + validator
    p.add_json_large(2, "extra IEEE reformat", fast_count=0)
    p.add_complete_small(2, "extra revision", fast_count=0)
    p.add_complete_small(10, "extra humanizer (2*5)", fast_count=0)
    p.add_embeddings(4, fast_count=0)
    p.notes_normal.append("2 extra expansion rounds (~16 LLM calls)")
    p.notes_fast.append("0 rounds (one-pass validator)")
    phases.append(p)

    return phases


def print_results(phases: list[Phase]):
    for mode in ("normal", "fast"):
        total_llm = 0
        total_firecrawl = 0
        total_embedding = 0
        total_all = 0

        label = "NORMAL MODE" if mode == "normal" else "FAST_MODE"
        print(f"\n{'=' * 70}")
        print(f"  {label}")
        print(f"{'=' * 70}")
        print(f"  {'Phase':<20} {'LLM calls':<12} {'Firecrawl':<12} {'Embed':<12} {'Total':<12}")
        print(f"  {'-' * 68}")

        for phase in phases:
            llm_n = phase.total_llm_count(mode)
            llm_ms = phase.total_llm_ms(mode)
            fc_n = phase.firecrawl_reqs_normal if mode == "normal" else phase.firecrawl_reqs_fast
            fc_ms = phase.total_firecrawl_ms(mode)
            emb_n = phase.embedding_calls_normal if mode == "normal" else phase.embedding_calls_fast
            emb_ms = phase.total_embedding_ms(mode)
            t = llm_ms + fc_ms + emb_ms

            total_llm += llm_n
            total_firecrawl += fc_n
            total_embedding += emb_n
            total_all += t

            notes = phase.notes_normal if mode == "normal" else phase.notes_fast
            note_str = f"  ({'; '.join(notes)})" if notes else ""
            print(
                f"  {phase.name:<20} {llm_n:<4} {format_ms(llm_ms):<8} "
                f"{fc_n:<4} {format_ms(fc_ms):<8} "
                f"{emb_n:<4} {format_ms(emb_ms):<8} "
                f"{format_ms(t):<8}{note_str}"
            )

        print(f"  {'-' * 68}")
        print(
            f"  {'TOTAL':<20} {total_llm:<4} {format_ms(sum(p.total_llm_ms(mode) for p in phases)):<8} "
            f"{total_firecrawl:<4} {format_ms(sum(p.total_firecrawl_ms(mode) for p in phases)):<8} "
            f"{total_embedding:<4} {format_ms(sum(p.total_embedding_ms(mode) for p in phases)):<8} "
            f"{format_ms(total_all):<8}"
        )

    # ── Side-by-side comparison ──
    print(f"\n{'=' * 70}")
    print("  COMPARISON")
    print(f"{'=' * 70}")

    normal_total = sum(p.total_ms("normal") for p in phases)
    fast_total = sum(p.total_ms("fast") for p in phases)
    savings = normal_total - fast_total
    pct = ((normal_total - fast_total) / normal_total) * 100

    print(f"  {'':<20} {'NORMAL':<20} {'FAST_MODE':<20} {'SAVINGS':<20}")
    print(f"  {'-' * 80}")
    print(
        f"  {'LLM calls':<20} {sum(p.total_llm_count('normal') for p in phases):<20} "
        f"{sum(p.total_llm_count('fast') for p in phases):<20} "
        f"{sum(p.total_llm_count('normal') for p in phases) - sum(p.total_llm_count('fast') for p in phases):<20}"
    )
    print(
        f"  {'Firecrawl reqs':<20} {sum(p.firecrawl_reqs_normal for p in phases):<20} "
        f"{sum(p.firecrawl_reqs_fast for p in phases):<20} "
        f"{sum(p.firecrawl_reqs_normal for p in phases) - sum(p.firecrawl_reqs_fast for p in phases):<20}"
    )
    print(
        f"  {'Embedding calls':<20} {sum(p.embedding_calls_normal for p in phases):<20} "
        f"{sum(p.embedding_calls_fast for p in phases):<20} "
        f"{sum(p.embedding_calls_normal for p in phases) - sum(p.embedding_calls_fast for p in phases):<20}"
    )
    print(
        f"  {'Total latency':<20} {format_ms(normal_total):<20} {format_ms(fast_total):<20} "
        f"{format_ms(savings):<20}"
    )
    print(f"  {'Reduction':<20} {'':<20} {'':<20} {pct:.0f}%")

    # ── Real-world estimate with overhead ──
    print(f"\n{'=' * 70}")
    print("  REAL-WORLD ESTIMATE (includes API overhead, cooldown, network)")
    print(f"{'=' * 70}")

    # Normal mode: 2x overhead from retries, failover, expansion loop toll
    normal_realistic = int(normal_total * 2.2)
    fast_realistic = int(fast_total * 1.3)  # Fast mode: much less overhead

    print(f"  {'Mode':<20} {'Estimated':<20} {'+ API overhead':<20} {'Total':<20}")
    print(f"  {'-' * 80}")
    print(
        f"  {'NORMAL':<20} {format_ms(normal_total):<20} {'+120%':<20} {format_ms(normal_realistic):<20}"
    )
    print(
        f"  {'FAST_MODE':<20} {format_ms(fast_total):<20} {'+30%':<20} {format_ms(fast_realistic):<20}"
    )
    print(f"  {'':<20} {'':<20} {'Savings':<20} {format_ms(normal_realistic - fast_realistic):<20}")

    print(f"\n  {'-' * 80}")
    print(f"  NORMAL mode:   {format_ms(normal_realistic)}  ({normal_realistic / 60_000:.1f} min)")
    print(f"  FAST_MODE:     {format_ms(fast_realistic)}  ({fast_realistic / 60_000:.1f} min)")
    print(f"  {'-' * 80}")

    under_10 = fast_realistic < 600_000
    check = "YES" if under_10 else "NO"
    emoji_check = "+" if under_10 else "-"
    print(f"\n  Target <10 min: {check} [{emoji_check}] ({format_ms(fast_realistic)} vs 10m)")
    if not under_10:
        print(f"  Overhead budget remaining: {format_ms(600_000 - fast_realistic)}")


async def main():
    phases = build_phases()
    print_results(phases)


if __name__ == "__main__":
    asyncio.run(main())
