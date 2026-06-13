"""
Agent 4: Reader Agent
Deeply reads and structures document content.
"""

from agents.base import BaseAgent
from services.llm import get_llm_client
from config.models import AgentRole
from schemas.agents import ReadDocument, ReaderOutput


READER_SYSTEM = """You are an expert academic document reader. Given web page content, extract and structure the key information.

Output valid JSON with this structure:
{
    "title": "Document title",
    "sections": [{"heading": "section name", "content": "key content"}],
    "key_findings": ["list of key findings"],
    "methodology": "methodology if present, null otherwise",
    "summary": "2-3 sentence summary of the document"
}

Rules:
- Extract factual information only
- Preserve specific numbers, dates, and technical details
- Identify methodology when present
- Summarize concisely but accurately"""


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

            # Truncate very long content
            content_truncated = content[:8000]

            user_prompt = f"""URL: {page.get('url', '')}
Title: {page.get('title', '')}

Content:
{content_truncated}

Extract and structure the key information as JSON."""

            try:
                result = await llm.complete_json(
                    role=AgentRole.READER,
                    system_prompt=READER_SYSTEM,
                    user_prompt=user_prompt,
                )

                doc = ReadDocument(
                    source_url=page.get("url", ""),
                    title=result.get("title", page.get("title", "")),
                    sections=result.get("sections", []),
                    key_findings=result.get("key_findings", []),
                    methodology=result.get("methodology"),
                    summary=result.get("summary", ""),
                )
                documents.append(doc)
            except Exception:
                # Skip documents that fail to parse
                continue

        output = ReaderOutput(documents=documents)
        return output.model_dump()

    def verify_output(self, output: dict) -> bool:
        if not super().verify_output(output):
            return False
        data = output.get("data", {})
        return len(data.get("documents", [])) > 0
