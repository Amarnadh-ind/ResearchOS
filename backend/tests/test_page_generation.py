import sys
import os
import pytest
import tempfile
from unittest.mock import AsyncMock, MagicMock

# Ensure backend directory is in the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.page_budget import compute_page_budget
from graph.nodes import page_validation_node

@pytest.mark.asyncio
async def test_page_validation_node_fails_fast_on_max_expansions(monkeypatch):
    # Setup state with low page count and max expansions
    state = {
        "pages": 12,
        "expansion_round": 4, # Max expansion round reached
        "target_word_count": 7200,
        "final_paper": {
            "title": "Low Page Count Test Paper",
            "abstract": "This is a short abstract.",
            "sections": [
                {
                    "heading": "I. Introduction",
                    "content": "Short intro content."
                }
            ],
            "references": ["[1] Source A"]
        }
    }
    
    # Mock embeddings to pass topic relevance
    async def mock_embed(query):
        return [1.0] * 384
    monkeypatch.setattr("retrieval.embeddings.embed_query", mock_embed)
    monkeypatch.setattr("retrieval.embeddings.cosine_similarity", lambda a, b: 0.90)
    
    # Mock compile_paper_to_pdf and count_pdf_pages to return 2 pages (which is < 12 target)
    async def mock_compile(paper, **kwargs):
        return b"Dummy PDF bytes"
    async def mock_count(pdf_path):
        return 2
        
    monkeypatch.setattr("services.pdf_generator.PDFGenerator.compile_paper_to_pdf", mock_compile)
    monkeypatch.setattr("services.pdf_generator.PDFGenerator.count_pdf_pages", mock_count)
    
    # Execute node
    res = await page_validation_node(state)
    
    assert res["status"] == "failed"
    assert "Page target not met" in res["error"]

@pytest.mark.asyncio
async def test_page_validation_node_loops_on_low_pages(monkeypatch):
    state = {
        "pages": 12,
        "expansion_round": 1, # Below max expansion limit (4)
        "target_word_count": 7200,
        "page_budget": {
            "section_budgets": {
                "I. Introduction": {"min_words": 800, "fraction": 0.12}
            }
        },
        "final_paper": {
            "title": "Low Page Count Test Paper",
            "abstract": "This is a short abstract.",
            "sections": [
                {
                    "heading": "I. Introduction",
                    "content": "Short intro content."
                }
            ],
            "references": ["[1] Source A"]
        }
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
    
    # Mock expand_paper_content to return expanded paper mock
    async def mock_expand(paper, *args, **kwargs):
        paper_copy = dict(paper)
        paper_copy["sections"] = [
            {
                "heading": "I. Introduction",
                "content": "Expanded intro content that is much longer now."
            }
        ]
        return paper_copy
        
    monkeypatch.setattr("graph.nodes.expand_paper_content", mock_expand)
    
    # Execute node
    res = await page_validation_node(state)
    
    assert res["current_agent"] == "page_validator"
    assert res["status"] == "validating_pages"
    assert res["expansion_round"] == 2
