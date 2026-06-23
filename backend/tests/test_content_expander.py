import os
import sys

import pytest

# Ensure backend directory is in the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.content_expander import (
    _classify_section,
    _detect_paper_topic,
    _heading_matches,
    expand_paper_content,
)


def test_detect_paper_topic():
    paper = {"title": "A Study on Model Context Protocol in Enterprise"}
    assert _detect_paper_topic(paper) == "mcp"

    paper2 = {"title": "ANFIS Control of Interleaved DC-DC Converter"}
    assert _detect_paper_topic(paper2) == "anfis"

    paper3 = {"title": "Crop Disease Detection using Vision Transformers"}
    assert _detect_paper_topic(paper3) == "crop"

    paper4 = {"title": "Modern Public Transit in India"}
    assert _detect_paper_topic(paper4) == "transport"

    paper5 = {"title": "Narratives of Bollywood in Indian Cinema"}
    assert _detect_paper_topic(paper5) == "cinema"

    paper6 = {"title": "Humanities, history, and culture of ancient Rome"}
    assert _detect_paper_topic(paper6) == "humanities"

    paper7 = {"title": "Some generic title"}
    assert _detect_paper_topic(paper7) == "generic"

def test_classify_section():
    assert _classify_section("I. Introduction") == "introduction"
    assert _classify_section("II. RELATED WORK") == "literature"
    assert _classify_section("IV. Proposed Methodology") == "methodology"
    assert _classify_section("VII. Results and Discussions") == "results"
    assert _classify_section("VIII. Comparative Analysis") == "comparison"
    assert _classify_section("IX. Conclusion") == "discussion"
    assert _classify_section("X. Future Scope") == "future_work"

def test_heading_matches():
    assert _heading_matches("I. INTRODUCTION", "I. INTRODUCTION")
    assert _heading_matches("I. INTRODUCTION", "INTRODUCTION")
    assert _heading_matches("II. LITERATURE REVIEW", "LITERATURE REVIEW / RELATED WORK")
    assert _heading_matches("LITERATURE REVIEW / RELATED WORK", "II. LITERATURE REVIEW")
    assert not _heading_matches("I. INTRODUCTION", "II. LITERATURE REVIEW")

@pytest.mark.asyncio
async def test_expand_paper_content_mock(monkeypatch):
    # Clear environment API keys to force mock behavior
    monkeypatch.setenv("OPENROUTER_API_KEY", "")
    monkeypatch.setenv("GEMINI_API_KEY", "")
    monkeypatch.setenv("GROK_API_KEY", "")
    monkeypatch.setenv("OPENAI_API_KEY", "")
    
    from config.settings import get_settings
    get_settings.cache_clear()

    # Setup paper data that is short
    paper = {
        "title": "Model Context Protocol",
        "abstract": "An abstract.",
        "sections": [
            {
                "heading": "I. INTRODUCTION",
                "content": "This is introductory content.",
                "subsections": []
            },
            {
                "heading": "II. LITERATURE REVIEW",
                "content": "This is literature review content.",
                "subsections": []
            }
        ],
        "conclusion": "Conclusion."
    }

    # Set MOCK_LLM environment variable to force mock expansion
    monkeypatch.setenv("MOCK_LLM", "True")
    
    # Target word count is much higher than current
    target_words = 1500
    expanded = await expand_paper_content(paper, target_words, topic="mcp")
    
    # Check that content has expanded (appended pre-built blocks)
    intro_content = expanded["sections"][0]["content"]
    lit_content = expanded["sections"][1]["content"]
    
    assert "proliferation of large language models" in intro_content
    assert "evolution of LLM-to-tool integration" in lit_content
    
    # Word count should be significantly higher
    from services.page_budget import count_paper_words
    stats = count_paper_words(expanded)
    assert stats["body_words"] > 500
