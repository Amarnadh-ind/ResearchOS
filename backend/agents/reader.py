"""
Agent 4: Reader Agent
Deeply reads and structures document content using LLM with content-aware segmentation.
"""

import structlog

from agents.base import BaseAgent
from config.models import AgentRole
from schemas.agents import ReadDocument, ReaderOutput
from services.llm import get_llm_client

logger = structlog.get_logger()

READER_SYSTEM = """You are an expert academic document reader. Given web page content, extract and structure the key information.

Output valid JSON with this structure:
{
    "title": "Document title",
    "sections": [{"heading": "section name", "content": "key content"}],
    "key_findings": ["list of key findings"],
    "methodology": "methodology if present, null otherwise",
    "summary": "2-3 sentence summary of the document",
    "authors": ["list of authors if mentioned"],
    "publication_date": "publication date if mentioned, null otherwise"
}

Rules:
- Extract factual information only
- Preserve specific numbers, dates, and technical details
- Identify methodology when present
- Summarize concisely but accurately
- Include author names and publication date when available"""


class ReaderAgent(BaseAgent):
    name = "reader"

    async def execute(self, input_data: dict, context: dict) -> dict:
        llm = get_llm_client()
        pages = input_data.get("pages", [])
        documents = []

        for page in pages:
            content = page.get("content", "")
            if len(content) < 100:
                continue

            doc = await self._process_page(llm, page, content)
            if doc:
                documents.append(doc)

        documents = self._deduplicate_documents(documents)

        logger.info("reader_completed", total_pages=len(pages), documents=len(documents))
        output = ReaderOutput(documents=documents)
        return output.model_dump()

    async def _process_page(self, llm, page: dict, content: str) -> ReadDocument | None:
        """Process a single page with smart content segmentation."""
        url = page.get("url", "")
        title = page.get("title", "")
        author = page.get("author") or ""
        pub_date = page.get("publication_date") or ""
        description = page.get("description") or ""

        from config.settings import get_settings

        content = self._segment_content(content)
        max_chars = 4000 if get_settings().fast_mode else 8000
        if len(content) > max_chars:
            content = content[:max_chars]

        metadata_line = f"URL: {url}\nTitle: {title}"
        if author:
            metadata_line += f"\nAuthor(s): {author}"
        if pub_date:
            metadata_line += f"\nPublication Date: {pub_date}"
        if description:
            metadata_line += f"\nDescription: {description}"

        user_prompt = f"""{metadata_line}

Content:
{content}

Extract and structure the key information as JSON."""

        try:
            result = await llm.complete_json(
                role=AgentRole.READER,
                system_prompt=READER_SYSTEM,
                user_prompt=user_prompt,
            )

            doc_title = result.get("title", title) or title or url
            doc = ReadDocument(
                source_url=url,
                title=doc_title,
                sections=result.get("sections", []),
                key_findings=result.get("key_findings", []),
                methodology=result.get("methodology"),
                summary=result.get("summary", ""),
            )
            return doc
        except Exception as e:
            logger.warning("reader_page_failed", url=url, error=str(e))
            return None

    @staticmethod
    def _segment_content(content: str) -> str:
        """Segment raw content into sections using markdown heading detection."""
        import re

        lines = content.split("\n")
        segments = []
        current_heading = ""
        current_lines = []

        for line in lines:
            heading_match = re.match(r"^(#{1,6})\s+(.+)$", line.strip())
            if heading_match:
                if current_lines:
                    body = " ".join(l.strip() for l in current_lines if l.strip())
                    if body:
                        segments.append(
                            f"**{current_heading}**: {body}" if current_heading else body
                        )
                current_heading = heading_match.group(2).strip()
                current_lines = []
            else:
                current_lines.append(line)

        if current_lines:
            body = " ".join(l.strip() for l in current_lines if l.strip())
            if body:
                segments.append(f"**{current_heading}**: {body}" if current_heading else body)

        result = "\n\n".join(segments) if segments else content
        return result[:10000]

    @staticmethod
    def _deduplicate_documents(docs: list[ReadDocument]) -> list[ReadDocument]:
        """Remove duplicate documents based on source_url."""
        seen = set()
        unique = []
        for doc in docs:
            if doc.source_url not in seen:
                seen.add(doc.source_url)
                unique.append(doc)
        return unique

    def verify_output(self, output: dict) -> bool:
        if not super().verify_output(output):
            return False
        data = output.get("data", {})
        return len(data.get("documents", [])) > 0
