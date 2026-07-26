"""
Hybrid RAG Orchestrator
Combines vector search + BM25 keyword search + reranking.
"""

import structlog

from retrieval.keyword import get_bm25_retriever
from retrieval.reranker import get_reranker
from retrieval.vector_store import get_vector_store

logger = structlog.get_logger()


class HybridRetriever:
    """Combines vector (semantic) and keyword (BM25) retrieval with reranking."""

    def __init__(self, vector_weight: float = 0.6, keyword_weight: float = 0.4):
        self.vector_weight = vector_weight
        self.keyword_weight = keyword_weight

    async def retrieve(
        self,
        query: str,
        limit: int = 10,
        session_id: str | None = None,
        rerank: bool = True,
    ) -> list[dict]:
        """Hybrid retrieval: vector + BM25 + optional reranking."""
        vector_store = get_vector_store()
        bm25 = get_bm25_retriever()

        # Run both retrievals
        vector_results = await vector_store.search(query, limit=limit * 2, session_id=session_id)
        keyword_results = bm25.search(query, limit=limit * 2)

        # Merge with reciprocal rank fusion
        merged = self._reciprocal_rank_fusion(vector_results, keyword_results)

        # Rerank if enabled
        if rerank and len(merged) > limit:
            reranker = get_reranker()
            merged = await reranker.rerank(query, merged, top_k=limit)
        else:
            merged = merged[:limit]

        logger.info(
            "hybrid_retrieval",
            query=query[:50],
            vector_hits=len(vector_results),
            keyword_hits=len(keyword_results),
            merged=len(merged),
        )

        return merged

    def _reciprocal_rank_fusion(
        self,
        vector_results: list[dict],
        keyword_results: list[dict],
        k: int = 60,
    ) -> list[dict]:
        """Merge results using Reciprocal Rank Fusion."""
        scores: dict[str, float] = {}
        doc_map: dict[str, dict] = {}

        # Score vector results
        for rank, doc in enumerate(vector_results):
            doc_key = doc.get("text", "")[:100]
            scores[doc_key] = scores.get(doc_key, 0) + self.vector_weight / (k + rank + 1)
            doc_map[doc_key] = doc

        # Score keyword results
        for rank, doc in enumerate(keyword_results):
            doc_key = doc.get("text", "")[:100]
            scores[doc_key] = scores.get(doc_key, 0) + self.keyword_weight / (k + rank + 1)
            if doc_key not in doc_map:
                doc_map[doc_key] = doc

        # Sort by fused score
        sorted_keys = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)

        results = []
        for key in sorted_keys:
            doc = doc_map[key].copy()
            doc["rrf_score"] = scores[key]
            results.append(doc)

        return results

    async def index_for_session(
        self,
        documents: list[dict],
        session_id: str,
    ):
        """Index documents for both vector and keyword retrieval."""
        vector_store = get_vector_store()
        bm25 = get_bm25_retriever()

        texts = [d.get("text", "") for d in documents]
        metas = [
            {"session_id": session_id, **{k: v for k, v in d.items() if k != "text"}}
            for d in documents
        ]

        # Vector index
        await vector_store.index_documents(texts, metas)

        # BM25 index
        bm25.index(documents)

        logger.info("session_indexed", session_id=session_id, docs=len(documents))


_hybrid: HybridRetriever | None = None


def get_hybrid_retriever() -> HybridRetriever:
    global _hybrid
    if _hybrid is None:
        _hybrid = HybridRetriever()
    return _hybrid
