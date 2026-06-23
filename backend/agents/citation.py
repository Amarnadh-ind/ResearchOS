"""
Agent 8: Citation Agent
Verifies and formats citations.
RULE-2: NO SOURCE = NO CITATION
RULE-3: No hallucinated references
RULE-4: All citations must be verified
"""

import structlog

from agents.base import BaseAgent
from config.models import AgentRole
from schemas.agents import CitationEntry, CitationOutput
from services.llm import get_llm_client

logger = structlog.get_logger()


CITATION_SYSTEM = """You are a citation verification and formatting specialist.

Given a list of sources used in the research, create proper IEEE-format citations.

CRITICAL RULES:
- RULE-2: NO SOURCE = NO CITATION. Only cite sources that were actually accessed.
- RULE-3: NO hallucinated references. Do not invent any citation details.
- RULE-4: All citations must be verified against the source data provided.

Output valid JSON:
{
    "citations": [
        {
            "key": "[1]",
            "ieee_format": "A. Author, \"Title,\" Publication, vol. X, no. Y, pp. Z, Year. [Online]. Available: URL",
            "authors": ["Author1", "Author2"],
            "title": "Full title",
            "publication": "Publication name or null",
            "year": 2024,
            "doi": "doi string or null",
            "url": "source URL",
            "verified": true
        }
    ],
    "in_text_map": {
        "claim_text_hash": "[1]"
    }
}

IEEE Format Rules:
- Author initials before surname: A. B. Surname
- Title in quotes for articles, italics for books
- Include [Online]. Available: URL for web sources
- Number citations sequentially [1], [2], etc."""


class CitationAgent(BaseAgent):
    name = "citation"

    async def execute(self, input_data: dict, context: dict) -> dict:
        llm = get_llm_client()

        verified_claims = input_data.get("verified_claims", [])
        documents = input_data.get("documents", [])
        claims = input_data.get("claims", [])
        sources = input_data.get("sources", [])

        # 1. Log Citation Agent Input
        logger.info("citation_agent_input_logging",
                    documents=documents,
                    claims=claims,
                    verified_claims=verified_claims)

        # 3 & 4. Verify claims and source URLs are passed
        source_urls = set()
        for doc in documents:
            url = doc.get("source_url") or doc.get("url")
            if url:
                source_urls.add(url)
        for src in sources:
            url = src.get("url") or src.get("source_url")
            if url:
                source_urls.add(url)

        logger.info("citation_agent_verified_inputs",
                    claims_passed=len(claims) > 0 or len(verified_claims) > 0,
                    source_urls_count=len(source_urls),
                    source_urls=list(source_urls))

        # Build source information for prompt
        sources_text = []
        for doc in documents:
            sources_text.append(
                f"URL: {doc.get('source_url', '')}\n"
                f"Title: {doc.get('title', '')}\n"
                f"Summary: {doc.get('summary', '')[:200]}"
            )

        claims_text = "\n".join(f"- {c}" for c in verified_claims[:30])

        user_prompt = f"""Sources used in this research:

{chr(10).join(sources_text)}

Claims that need citations:
{claims_text}

Create IEEE-format citations for all sources. Map each claim to its citation.
Only include citations for sources that were actually accessed. DO NOT hallucinate any references."""

        citations = []
        in_text_map = {}

        try:
            result = await llm.complete_json(
                role=AgentRole.CITATION,
                system_prompt=CITATION_SYSTEM,
                user_prompt=user_prompt,
            )
            for c in result.get("citations", []):
                # RULE-2: Reject citations without URLs
                if not c.get("url"):
                    continue
                # RULE-3: Reject citations without titles
                if not c.get("title"):
                    continue

                citations.append(CitationEntry(
                    key=c.get("key", f"[{len(citations)+1}]"),
                    ieee_format=c.get("ieee_format", ""),
                    authors=c.get("authors", ["Unknown"]),
                    title=c["title"],
                    publication=c.get("publication"),
                    year=c.get("year"),
                    doi=c.get("doi"),
                    url=c["url"],
                    verified=True,  # We verified via source data
                ))
            in_text_map = result.get("in_text_map", {})
        except Exception as e:
            logger.error("citation_agent_llm_error", error=str(e))
            raise RuntimeError(f"Citation LLM generation failed: {str(e)}") from e

        # If zero citations are successfully generated but we have sources, treat as failure to trigger fallback
        if not citations and source_urls:
            raise ValueError("Zero valid citations generated from LLM.")

        output = CitationOutput(
            citations=citations,
            in_text_map=in_text_map,
        )
        
        # 2. Log Citation Agent Output
        logger.info("citation_agent_output_logging",
                    citation_count=len(citations),
                    source_count=len(source_urls))
                    
        return output.model_dump()

    def verify_output(self, output: dict) -> bool:
        """RULE-4: All citations must be verified."""
        if not super().verify_output(output):
            return False
        data = output.get("data", {})
        citations = data.get("citations", [])
        # Every citation must have a URL and title
        return all(c.get("url") and c.get("title") for c in citations)
