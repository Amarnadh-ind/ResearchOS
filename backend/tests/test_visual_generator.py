import os
import sys

# Ensure backend directory is in the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.visual_generator import (
    generate_architecture_svg,
    generate_bar_chart_svg,
    generate_line_chart_svg,
    generate_pie_chart_svg,
    generate_visuals_for_topic,
    inject_visuals_into_paper,
)


def test_generate_bar_chart_svg():
    categories = ["Cat A", "Cat B"]
    values = [10.5, 20.3]
    svg = generate_bar_chart_svg("Test Bar Chart", categories, values)
    assert "<svg" in svg
    assert "</svg>" in svg
    assert "Test Bar Chart" in svg
    assert "Cat A" in svg
    assert "10.5" in svg


def test_generate_line_chart_svg():
    x_labels = ["2020", "2021", "2022"]
    series = {"Series 1": [1.0, 2.0, 3.0]}
    svg = generate_line_chart_svg("Test Line Chart", x_labels, series)
    assert "<svg" in svg
    assert "</svg>" in svg
    assert "Test Line Chart" in svg
    assert "Series 1" in svg


def test_generate_pie_chart_svg():
    labels = ["A", "B"]
    values = [40, 60]
    svg = generate_pie_chart_svg("Test Pie Chart", labels, values)
    assert "<svg" in svg
    assert "</svg>" in svg
    assert "Test Pie Chart" in svg
    assert "A (40%)" in svg


def test_generate_architecture_svg():
    blocks = ["Block 1", "Block 2"]
    svg = generate_architecture_svg("Test Arch", blocks)
    assert "<svg" in svg
    assert "</svg>" in svg
    assert "Test Arch" in svg
    assert "Block 1" in svg
    assert "arrowhead" in svg


def test_generate_visuals_for_topic():
    # Test for MCP topic
    mcp_visuals = generate_visuals_for_topic("Model Context Protocol", [], target_figures=3)
    assert len(mcp_visuals) > 0
    assert (
        "Model Context Protocol" in mcp_visuals[0]["caption"]
        or "protocol" in mcp_visuals[0]["caption"].lower()
    )


def test_inject_visuals_into_paper():
    paper = {
        "title": "A Study on Model Context Protocol",
        "abstract": "Abstract",
        "sections": [
            {"heading": "I. INTRODUCTION", "content": "Paragraph one.", "subsections": []},
            {
                "heading": "IV. PROPOSED METHODOLOGY / SYSTEM MODEL",
                "content": "Paragraph two.",
                "subsections": [],
            },
            {
                "heading": "VII. RESULTS AND DISCUSSION",
                "content": "Paragraph three.",
                "subsections": [],
            },
        ],
        "references": [],
    }

    injected = inject_visuals_into_paper(paper, "Model Context Protocol", target_figures=3)

    # Check that SVG tags were injected into section content
    has_svg = False
    for sec in injected["sections"]:
        if "<svg" in sec["content"]:
            has_svg = True
            break

    assert has_svg
