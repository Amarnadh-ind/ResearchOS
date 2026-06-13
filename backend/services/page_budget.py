"""
Page Budget Calculator
Converts target page count into word count targets with section-level allocations.

IEEE double-column ≈ 600 words/page (with figures/tables/equations/refs).
Single column ≈ 350 words/page.
"""

import structlog

logger = structlog.get_logger()

# Words per page by layout type (strictly mapped to 650 words/page)
WORDS_PER_PAGE = {
    "1 Column": 650,
    "2 Column": 650,
    "Multi Column": 650,
}

# Section allocation as fraction of total word budget
# These fractions exclude Abstract and References (handled separately)
SECTION_ALLOCATIONS = {
    "I. INTRODUCTION": 0.12,
    "II. LITERATURE REVIEW": 0.16,
    "III. PROBLEM STATEMENT AND RESEARCH GAP": 0.08,
    "IV. PROPOSED METHODOLOGY": 0.16,
    "V. MATHEMATICAL MODELING": 0.10,
    "VI. EXPERIMENTAL SETUP AND SIMULATION": 0.10,
    "VII. RESULTS AND DISCUSSION": 0.14,
    "VIII. COMPARATIVE ANALYSIS": 0.06,
    "IX. CONCLUSION": 0.05,
    "X. FUTURE SCOPE": 0.03,
}

# Minimum words for a figure/table placeholder block
FIGURE_WORD_EQUIVALENT = 120  # A figure + caption ≈ 120 words of space
MIN_FIGURES = 5


def compute_page_budget(
    target_pages: int,
    layout: str = "2 Column",
    expected_sections: list[str] | None = None,
) -> dict:
    """Compute word budget for a paper.

    Returns:
        {
            "target_pages": 12,
            "layout": "2 Column",
            "words_per_page": 600,
            "total_word_target": 7200,
            "body_word_target": 6600,     # excludes abstract (~200) + refs (~400)
            "abstract_word_target": 200,
            "min_figures": 5,
            "figure_word_equivalent": 600,  # 5 figures × 120
            "section_budgets": {
                "I. INTRODUCTION": {"min_words": 790, "fraction": 0.12},
                ...
            }
        }
    """
    words_per_page = WORDS_PER_PAGE.get(layout, 650)
    total_word_target = target_pages * words_per_page

    # Abstract and references consume ~600 words of space
    abstract_target = 200
    references_space = 400  # ~25 refs ≈ 400 words of space
    body_word_target = total_word_target - abstract_target - references_space

    # Figure space deduction from body (figures replace text space)
    figure_space = MIN_FIGURES * FIGURE_WORD_EQUIVALENT

    # Map sections to budgets
    # If expected_sections are provided and they match known allocations, use them.
    # Otherwise, use the default allocation keys.
    allocations = {}
    remaining_fraction = 1.0

    if expected_sections and len(expected_sections) >= 5:
        # Map expected sections to default fractions by order
        default_fracs = list(SECTION_ALLOCATIONS.values())
        for idx, sec_name in enumerate(expected_sections):
            sec_name_clean = sec_name.strip()
            if "REFERENCES" in sec_name_clean.upper() or "BIBLIOGRAPHY" in sec_name_clean.upper():
                continue  # Skip references section
            frac = default_fracs[idx] if idx < len(default_fracs) else 0.05
            allocations[sec_name_clean] = frac
    else:
        allocations = dict(SECTION_ALLOCATIONS)

    # Normalize fractions
    total_frac = sum(allocations.values())
    if total_frac > 0:
        allocations = {k: v / total_frac for k, v in allocations.items()}

    section_budgets = {}
    for section_name, fraction in allocations.items():
        min_words = max(int(body_word_target * fraction), 200)
        section_budgets[section_name] = {
            "min_words": min_words,
            "fraction": round(fraction, 3),
        }

    budget = {
        "target_pages": target_pages,
        "layout": layout,
        "words_per_page": words_per_page,
        "total_word_target": total_word_target,
        "body_word_target": body_word_target,
        "abstract_word_target": abstract_target,
        "min_figures": MIN_FIGURES,
        "figure_word_equivalent": figure_space,
        "section_budgets": section_budgets,
    }

    logger.info(
        "page_budget_computed",
        target_pages=target_pages,
        total_words=total_word_target,
        body_words=body_word_target,
        sections=len(section_budgets),
    )
    return budget


def count_words(text: str) -> int:
    """Count words in a text string, ignoring HTML tags and markdown syntax."""
    import re
    # Strip HTML tags
    clean = re.sub(r'<[^>]+>', ' ', text)
    # Strip markdown syntax
    clean = re.sub(r'[#*_`\[\]()!]', ' ', clean)
    # Strip LaTeX/math
    clean = re.sub(r'\$\$.*?\$\$', ' EQUATION ', clean, flags=re.DOTALL)
    clean = re.sub(r'\$.*?\$', ' EXPR ', clean)
    return len(clean.split())


def count_paper_words(paper_data: dict) -> dict:
    """Count words in each section of a paper and return breakdown.

    Returns:
        {
            "total_words": 7200,
            "abstract_words": 200,
            "body_words": 6600,
            "section_words": {"I. INTRODUCTION": 800, ...},
            "conclusion_words": 350,
        }
    """
    abstract_words = count_words(paper_data.get("abstract", ""))

    section_words = {}
    body_total = 0
    for section in paper_data.get("sections", []):
        heading = section.get("heading", "Unnamed")
        content = section.get("content", "")
        # Include subsections
        for sub in section.get("subsections", []):
            content += " " + sub.get("content", "")
        wc = count_words(content)
        section_words[heading] = wc
        body_total += wc

    conclusion_words = count_words(paper_data.get("conclusion", ""))
    body_total += conclusion_words

    return {
        "total_words": abstract_words + body_total,
        "abstract_words": abstract_words,
        "body_words": body_total,
        "section_words": section_words,
        "conclusion_words": conclusion_words,
    }
