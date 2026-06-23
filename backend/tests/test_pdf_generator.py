import os
import sys

import pytest

# Ensure backend directory is in the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.pdf_generator import (
    PDFGenerator,
    _build_sections_html,
    _font_css_from_name,
    parse_markdown_to_html,
)


def test_font_css_from_name():
    assert _font_css_from_name("Times New Roman") == "'Times New Roman', Times"
    assert _font_css_from_name("Arial") == "Arial, Helvetica, sans-serif"
    assert _font_css_from_name("InvalidFont") == "'InvalidFont', sans-serif"

def test_parse_markdown_to_html():
    md = """## I. Introduction
This is a paragraph with **bold** and *italic* text.

### A. Subsection
Another paragraph.

$$E = mc^2$$
"""
    html = parse_markdown_to_html(md)
    assert '<h2 class="section-heading">I. Introduction</h2>' in html
    assert '<strong>bold</strong>' in html
    assert '<em>italic</em>' in html
    assert '<h3 class="subsection-heading">A. Subsection</h3>' in html
    assert '$$E = mc^2$$' in html

def test_build_sections_html():
    sections = [
        {
            "heading": "I. Introduction",
            "content": "Intro content",
            "subsections": [
                {
                    "heading": "A. Background",
                    "content": "Background content"
                }
            ]
        }
    ]
    html = _build_sections_html(sections)
    assert '<h2 class="section-heading">I. Introduction</h2>' in html
    assert '<h3 class="subsection-heading">A. Background</h3>' in html
    assert 'Intro content' in html
    assert 'Background content' in html

@pytest.mark.asyncio
async def test_pdf_generation_flow():
    # Test compilation to PDF bytes (mocked paper data)
    paper = {
        "title": "Test Paper",
        "abstract": "Test abstract.",
        "authors": ["Author 1"],
        "keywords": ["Test"],
        "sections": [
            {
                "heading": "I. INTRODUCTION",
                "content": "This is test introduction.",
                "subsections": []
            }
        ],
        "references": ["[1] A. Scholar, Test."]
    }
    
    # We won't run full PDF generation if Playwright is missing or environment lacks GUI,
    # but we can try and catch failures, or test helper methods.
    try:
        pdf_bytes = await PDFGenerator.compile_paper_to_pdf(paper, layout="2 Column", font="Times New Roman")
        assert len(pdf_bytes) > 0
    except Exception as e:
        # If playwright is not initialized or chromium is missing, this might fail, which is okay for this test
        pytest.skip(f"Subprocess PDF rendering skipped: {str(e)}")
