import os
import sys
from unittest.mock import MagicMock

import pytest

# Ensure backend directory is in the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agents.humanizer import HumanizerAgent
from graph.nodes import humanizer_node


@pytest.mark.asyncio
async def test_humanizer_agent_bypasses_tables_equations_figures(monkeypatch):
    agent = HumanizerAgent()

    # Sample paper structure with prose, table, equations, and SVG figure
    sample_paper = {
        "title": "A Great Paper",
        "abstract": "This is a machine abstract. We investigate the Model Context Protocol.",
        "sections": [
            {
                "heading": "I. INTRODUCTION",
                "content": (
                    "First prose paragraph. The Model Context Protocol establishes clean boundaries [1].\n\n"
                    "| Col 1 | Col 2 |\n|---|---|\n| A | B |\n\n"
                    "$$x + y = z$$\n\n"
                    '<div class="figure"><svg><rect/></svg></div>\n\n'
                    "Second prose paragraph. We evaluate the stdio transport layer [2]."
                ),
                "subsections": [],
            }
        ],
        "conclusion": "To conclude, the proposed methodology yields high performance.",
    }

    call_count = [0]

    # Mock LLM complete to return a humanized version of prose based on prompt content
    async def mock_complete(role, system_prompt, user_prompt, temperature=None, max_tokens=None):
        call_count[0] += 1
        if "abstract" in user_prompt:
            return "This abstract has been humanized. We study Model Context Protocol."
        elif "First prose" in user_prompt:
            return (
                "Rewritten first paragraph. The Model Context Protocol establishes clean boundaries [1].\n\n"
                "| Col 1 | Col 2 |\n|---|---|\n| A | B |\n\n"
                "$$x + y = z$$\n\n"
                '<div class="figure"><svg><rect/></svg></div>\n\n'
                "Rewritten second paragraph. We evaluate the stdio transport layer [2]."
            )
        elif "conclude" in user_prompt:
            return "To summarize, our proposed framework offers stellar performance."
        return user_prompt

    # Mock the LLM client
    mock_llm_client = MagicMock()
    mock_llm_client.complete = mock_complete
    monkeypatch.setattr("agents.humanizer.get_llm_client", lambda: mock_llm_client)

    result = await agent.humanize_paper(sample_paper)

    # Assertions
    assert result["title"] == "A Great Paper"
    assert "humanized" in result["abstract"]
    assert "summarize" in result["conclusion"]

    # Assert non-prose elements are exactly preserved
    content = result["sections"][0]["content"]
    assert "| Col 1 | Col 2 |" in content
    assert "$$x + y = z$$" in content
    assert '<div class="figure"><svg><rect/></svg></div>' in content

    # Assert inline citations are preserved
    assert "[1]" in content
    assert "[2]" in content

    # Assert LLM was called once for each section (abstract, introduction, conclusion)
    assert call_count[0] == 3


@pytest.mark.asyncio
async def test_humanizer_node_success(monkeypatch):
    monkeypatch.setenv("NEMOTRON_API_KEY", "test")
    monkeypatch.setenv("MANUS_API_KEY", "test")
    from config.settings import get_settings

    get_settings.cache_clear()
    s = get_settings()
    s.fast_mode = False

    state = {
        "topic": "Model Context Protocol",
        "final_paper": {
            "title": "A Great Paper",
            "abstract": "Machine abstract.",
            "sections": [
                {"heading": "I. INTRODUCTION", "content": "First paragraph.", "subsections": []}
            ],
            "conclusion": "To conclude.",
        },
    }

    # Mock HumanizerAgent humanize_paper
    async def mock_humanize_paper(self, paper):
        paper_copy = dict(paper)
        paper_copy["abstract"] = "Humanized abstract."
        return paper_copy

    monkeypatch.setattr(HumanizerAgent, "humanize_paper", mock_humanize_paper)

    # Mock _build_markdown in IEEEFormatter
    monkeypatch.setattr(
        "agents.ieee_formatter.IEEEFormatterAgent._build_markdown", lambda self, p: "Mock Markdown"
    )

    res = await humanizer_node(state)

    assert res["current_agent"] == "humanizer"
    assert res["status"] == "validating_pages"
    assert res["final_paper"]["abstract"] == "Humanized abstract."
    assert res["content_markdown"] == "Mock Markdown"
