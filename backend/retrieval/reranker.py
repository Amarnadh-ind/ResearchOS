"""
Reranker
Cross-encoder reranking for improved retrieval precision.
Uses LLM-based reranking via OpenRouter when cross-encoder is unavailable.
"""

import structlog

from config.models import AgentRole
from services.llm import get_llm_client

logger = structlog.get_logger()


class Reranker:
    """Rerank search results for improved precision."""

    async def rerank(
        self,
        query: str,
        documents: list[dict],
        top_k: int = 10,
    ) -> list[dict]:
        """Rerank documents based on relevance to query."""
        if len(documents) <= top_k:
            return documents

        # Use LLM-based reranking
        llm = get_llm_client()

        doc_texts = []
        for i, doc in enumerate(documents[:20]):  # Cap at 20 for LLM context
            text = doc.get("text", "")[:300]
            doc_texts.append(f"[{i}] {text}")

        prompt = f"""Given the query: "{query}"

Rank the following documents by relevance. Return ONLY a JSON array of document indices in order of relevance (most relevant first).

Documents:
{chr(10).join(doc_texts)}

Return format: {{"ranking": [0, 3, 1, ...]}}"""

        try:
            result = await llm.complete_json(
                role=AgentRole.WORKER,
                system_prompt="You are a document relevance ranker. Return only the JSON ranking.",
                user_prompt=prompt,
            )

            ranking = result.get("ranking", list(range(len(documents))))
            reranked = []
            for idx in ranking[:top_k]:
                if 0 <= idx < len(documents):
                    doc = documents[idx].copy()
                    doc["rerank_position"] = len(reranked)
                    reranked.append(doc)

            logger.info("reranked", query=query[:50], results=len(reranked))
            return reranked

        except Exception as e:
            logger.warning("rerank_fallback", error=str(e))
            # Fallback: return top-k as-is
            return documents[:top_k]


_reranker: Reranker | None = None


def get_reranker() -> Reranker:
    global _reranker
    if _reranker is None:
        _reranker = Reranker()
    return _reranker
