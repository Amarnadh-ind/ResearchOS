import asyncio
import sys

sys.path.insert(0, r"d:\research os\backend")
from services.content_expander import expand_paper_content
from services.mock_llm import _build_generic_writer
from services.page_budget import compute_page_budget, count_paper_words


async def main():
    # Get budget
    budget = compute_page_budget(12)
    target = budget["body_word_target"]

    # Get mock output
    writer = _build_generic_writer("Autonomous Multi-Agent Systems")
    stats_before = count_paper_words(writer)
    print(f"BEFORE expansion: {stats_before['body_words']} body words (target: {target})")

    # Expand
    expanded = await expand_paper_content(writer, target, budget["section_budgets"])
    stats_after = count_paper_words(expanded)
    print(f"AFTER expansion:  {stats_after['body_words']} body words (target: {target})")
    print(f"Ratio: {stats_after['body_words']/target:.1%}")
    print("\nSection breakdown:")
    for sec, wc in stats_after["section_words"].items():
        print(f"  {sec}: {wc}")

if __name__ == "__main__":
    asyncio.run(main())
