import sys
sys.path.insert(0, r"d:\research os\backend")
from services.page_budget import compute_page_budget, count_words, count_paper_words

b = compute_page_budget(12)
print(f"Target: {b['target_pages']} pages, {b['total_word_target']} words")
print(f"Body target: {b['body_word_target']} words")
print(f"Sections: {len(b['section_budgets'])}")
for k, v in b["section_budgets"].items():
    print(f"  {k}: {v['min_words']} words")

# Test mock writer word count
from services.mock_llm import _build_generic_writer
writer = _build_generic_writer("Autonomous Multi-Agent Systems")
stats = count_paper_words(writer)
print(f"\nMock writer output:")
print(f"  Total words: {stats['total_words']}")
print(f"  Body words: {stats['body_words']}")
print(f"  Abstract: {stats['abstract_words']}")
for sec, wc in stats["section_words"].items():
    print(f"  {sec}: {wc}")
