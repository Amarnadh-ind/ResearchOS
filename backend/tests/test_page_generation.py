import os
import sys

import pytest

# Ensure backend directory is in the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from graph.nodes import page_validation_node


@pytest.mark.asyncio
async def test_page_validation_node_fails_fast_on_max_expansions(monkeypatch):
    """Page validation no longer loops — always finalizes regardless of page count."""
    from config.settings import get_settings

    get_settings.cache_clear()
    get_settings().fast_mode = False

    state = {
        "pages": 12,
        "expansion_round": 4,
        "target_word_count": 7200,
        "final_paper": {
            "title": "Low Page Count Test Paper",
            "abstract": "This is a short abstract.",
            "sections": [{"heading": "I. Introduction", "content": "Short intro content."}],
            "references": ["[1] Source A"],
        },
    }

    # Mock embeddings to pass topic relevance
    async def mock_embed(query):
        return [1.0] * 384

    monkeypatch.setattr("retrieval.embeddings.embed_query", mock_embed)
    monkeypatch.setattr("retrieval.embeddings.cosine_similarity", lambda a, b: 0.90)

    # Mock compile_paper_to_pdf and count_pdf_pages to return 2 pages
    async def mock_compile(paper, **kwargs):
        return b"Dummy PDF bytes"

    async def mock_count(pdf_path):
        return 2

    monkeypatch.setattr("services.pdf_generator.PDFGenerator.compile_paper_to_pdf", mock_compile)
    monkeypatch.setattr("services.pdf_generator.PDFGenerator.count_pdf_pages", mock_count)

    res = await page_validation_node(state)

    # One-pass validation: always completes, no loops
    assert res["status"] == "completed"
    assert res["current_agent"] == "done"
    assert res["validation"]["page_count_achieved"] is False
    assert res["validation"]["actual_pages"] == 2


@pytest.mark.asyncio
async def test_page_validation_node_completes_one_pass(monkeypatch):
    """Page validator runs once and finalizes — no loops back to self."""
    from config.settings import get_settings

    get_settings.cache_clear()
    get_settings().fast_mode = False

    state = {
        "pages": 12,
        "expansion_round": 1,
        "target_word_count": 7200,
        "page_budget": {
            "section_budgets": {"I. Introduction": {"min_words": 800, "fraction": 0.12}}
        },
        "final_paper": {
            "title": "Low Page Count Test Paper",
            "abstract": "This is a short abstract.",
            "sections": [{"heading": "I. Introduction", "content": "Short intro content."}],
            "references": ["[1] Source A"],
        },
    }

    # Mock embeddings
    async def mock_embed(query):
        return [1.0] * 384

    monkeypatch.setattr("retrieval.embeddings.embed_query", mock_embed)
    monkeypatch.setattr("retrieval.embeddings.cosine_similarity", lambda a, b: 0.90)

    # Mock PDF compiler to return 3 pages
    async def mock_compile(paper, **kwargs):
        return b"Dummy PDF bytes"

    async def mock_count(pdf_path):
        return 3

    monkeypatch.setattr("services.pdf_generator.PDFGenerator.compile_paper_to_pdf", mock_compile)
    monkeypatch.setattr("services.pdf_generator.PDFGenerator.count_pdf_pages", mock_count)

    res = await page_validation_node(state)

    # One-pass: completes immediately, no loop, no expansion
    assert res["current_agent"] == "done"
    assert res["status"] == "completed"
