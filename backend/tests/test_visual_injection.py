import os
import sys

# Ensure backend directory is in the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.visual_generator import generate_visuals_for_topic, inject_visuals_into_paper


def test_generate_visuals_for_topic_count():
    topic = "Optimal Control of Interleaved DC-DC Converter"
    sections = []

    # Target 3 figures
    figs_3 = generate_visuals_for_topic(topic, sections, target_figures=3)
    assert len(figs_3) == 3

    # Target 6 figures
    figs_6 = generate_visuals_for_topic(topic, sections, target_figures=6)
    assert len(figs_6) == 6


def test_generate_visuals_contains_svg_and_captions():
    topic = "Optimal Control of Interleaved DC-DC Converter"
    sections = []
    figs = generate_visuals_for_topic(topic, sections, target_figures=3)

    for i, fig in enumerate(figs):
        assert "svg" in fig
        assert (
            fig["svg"].startswith("<svg") or fig["svg"].startswith("\n<svg") or "<svg" in fig["svg"]
        )
        assert "caption" in fig
        assert fig["caption"].startswith(f"Fig. {i + 1}.")


def test_inject_visuals_into_paper_placement():
    topic = "Optimal Control of Interleaved DC-DC Converter"
    paper = {
        "title": "A Test Paper on Converter Control",
        "abstract": "This is abstract.",
        "sections": [
            {"heading": "I. Introduction", "content": "Introductory content."},
            {"heading": "II. Proposed Methodology", "content": "Methodology content."},
            {"heading": "III. Experimental Results", "content": "Results content."},
        ],
    }

    injected_paper = inject_visuals_into_paper(paper, topic, target_figures=3)

    # Confirm content now contains figure-container class
    injected_count = 0
    for sec in injected_paper["sections"]:
        if "figure-container" in sec["content"]:
            injected_count += sec["content"].count("figure-container")

    # Each figure should have a container, so we expect exactly 3 figure containers
    assert injected_count == 3
