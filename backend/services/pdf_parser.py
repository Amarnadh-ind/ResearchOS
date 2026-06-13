"""
PDF Parser Service
PyMuPDF-based document parsing with section detection.
"""

import io
import structlog
import fitz  # PyMuPDF

logger = structlog.get_logger()


class PDFParser:
    """Parse PDF documents and extract structured content."""

    async def parse_pdf(self, pdf_bytes: bytes) -> dict:
        """Parse a PDF and return structured content."""
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            result = {
                "title": self._extract_title(doc),
                "pages": doc.page_count,
                "sections": [],
                "full_text": "",
                "metadata": dict(doc.metadata) if doc.metadata else {},
            }

            full_text_parts = []
            current_section = {"heading": "Introduction", "content": ""}

            for page_num in range(doc.page_count):
                page = doc[page_num]
                blocks = page.get_text("dict")["blocks"]

                for block in blocks:
                    if block["type"] != 0:  # Skip non-text blocks
                        continue

                    for line in block.get("lines", []):
                        text = ""
                        is_heading = False

                        for span in line.get("spans", []):
                            text += span["text"]
                            # Detect headings by font size
                            if span["size"] > 13 or "bold" in span["font"].lower():
                                is_heading = True

                        text = text.strip()
                        if not text:
                            continue

                        if is_heading and len(text) > 3 and len(text) < 200:
                            # Save current section
                            if current_section["content"].strip():
                                result["sections"].append(current_section.copy())
                            current_section = {"heading": text, "content": ""}
                        else:
                            current_section["content"] += text + " "

                        full_text_parts.append(text)

            # Save last section
            if current_section["content"].strip():
                result["sections"].append(current_section)

            result["full_text"] = "\n".join(full_text_parts)
            doc.close()

            logger.info(
                "pdf_parsed",
                pages=result["pages"],
                sections=len(result["sections"]),
            )
            return result

        except Exception as e:
            logger.error("pdf_parse_error", error=str(e))
            return {
                "title": "Parse Error",
                "pages": 0,
                "sections": [],
                "full_text": "",
                "metadata": {},
                "error": str(e),
            }

    def _extract_title(self, doc: fitz.Document) -> str:
        """Extract title from PDF metadata or first page."""
        if doc.metadata and doc.metadata.get("title"):
            return doc.metadata["title"]

        # Try first page, largest font
        if doc.page_count > 0:
            page = doc[0]
            blocks = page.get_text("dict")["blocks"]
            max_size = 0
            title = ""
            for block in blocks:
                if block["type"] != 0:
                    continue
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        if span["size"] > max_size:
                            max_size = span["size"]
                            title = span["text"].strip()
            return title or "Untitled Document"

        return "Untitled Document"

    async def parse_from_url(self, url: str) -> dict:
        """Download and parse a PDF from URL."""
        import httpx

        try:
            async with httpx.AsyncClient(follow_redirects=True) as client:
                response = await client.get(url, timeout=60.0)
                response.raise_for_status()
                return await self.parse_pdf(response.content)
        except Exception as e:
            logger.error("pdf_download_error", url=url, error=str(e))
            return {"title": "Download Error", "sections": [], "full_text": "", "error": str(e)}


_pdf_parser: PDFParser | None = None


def get_pdf_parser() -> PDFParser:
    global _pdf_parser
    if _pdf_parser is None:
        _pdf_parser = PDFParser()
    return _pdf_parser
