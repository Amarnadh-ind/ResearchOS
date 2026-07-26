"""
Layer 2: Retrieval Memory (Qdrant)
Vector storage for semantic document retrieval.
"""

import uuid

import structlog
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

from config.settings import get_settings

logger = structlog.get_logger()


class RetrievalMemory:
    """Qdrant-backed vector storage for semantic retrieval.
    Falls back to in-memory list when Qdrant is unavailable."""

    def __init__(self):
        settings = get_settings()
        self._client: AsyncQdrantClient | None = None
        self._host = settings.qdrant_host
        self._port = settings.qdrant_port
        self._collection = settings.qdrant_collection
        self._dimension = settings.embedding_dimension
        self._using_fallback = False
        self._in_memory_store: list[dict] = []

    async def connect(self):
        if self._client is None and not self._using_fallback:
            try:
                self._client = AsyncQdrantClient(host=self._host, port=self._port)
                # Ensure collection exists
                collections = await self._client.get_collections()
                names = [c.name for c in collections.collections]
                if self._collection not in names:
                    await self._client.create_collection(
                        collection_name=self._collection,
                        vectors_config=VectorParams(
                            size=self._dimension,
                            distance=Distance.COSINE,
                        ),
                    )
                    logger.info("qdrant_collection_created", name=self._collection)
                logger.info("qdrant_connected")
            except Exception as e:
                logger.warning("qdrant_unavailable_using_memory", error=str(e))
                self._using_fallback = True

    async def disconnect(self):
        if self._client:
            await self._client.close()
            self._client = None

    async def upsert_documents(
        self,
        texts: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict],
    ):
        """Store document chunks with embeddings."""
        if self._using_fallback:
            for text, embedding, meta in zip(texts, embeddings, metadatas):
                self._in_memory_store.append(
                    {
                        "text": text,
                        "vector": embedding,
                        **meta,
                    }
                )
            logger.info("in_memory_upserted", count=len(texts))
            return
        await self.connect()

        points = []
        for text, embedding, meta in zip(texts, embeddings, metadatas):
            point_id = str(uuid.uuid4())
            points.append(
                PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload={
                        "text": text,
                        **meta,
                    },
                )
            )

        await self._client.upsert(
            collection_name=self._collection,
            points=points,
        )
        logger.info("qdrant_upserted", count=len(points))

    async def search(
        self,
        query_embedding: list[float],
        limit: int = 10,
        session_id: str | None = None,
    ) -> list[dict]:
        """Semantic search over stored documents."""
        if self._using_fallback:
            # Simple cosine similarity search over in-memory store
            import numpy as np

            results = []
            q = np.array(query_embedding)
            q_norm = np.linalg.norm(q)
            if q_norm == 0:
                return []
            for doc in self._in_memory_store:
                if session_id and doc.get("session_id") != session_id:
                    continue
                v = np.array(doc.get("vector", []))
                if len(v) == 0:
                    continue
                score = float(np.dot(q, v) / (q_norm * np.linalg.norm(v) + 1e-8))
                results.append(
                    {
                        "id": str(len(results)),
                        "score": score,
                        "text": doc.get("text", ""),
                        **{k: v for k, v in doc.items() if k not in ("text", "vector")},
                    }
                )
            results.sort(key=lambda x: x["score"], reverse=True)
            return results[:limit]
        await self.connect()

        query_filter = None
        if session_id:
            query_filter = Filter(
                must=[
                    FieldCondition(
                        key="session_id",
                        match=MatchValue(value=session_id),
                    )
                ]
            )

        results = await self._client.search(
            collection_name=self._collection,
            query_vector=query_embedding,
            limit=limit,
            query_filter=query_filter,
        )

        return [
            {
                "id": str(r.id),
                "score": r.score,
                "text": r.payload.get("text", ""),
                **{k: v for k, v in r.payload.items() if k != "text"},
            }
            for r in results
        ]

    async def clear(self):
        """Clear all stored vectors by dropping and recreating the collection."""
        if self._using_fallback:
            self._in_memory_store.clear()
            logger.info("in_memory_store_cleared")
            return
        await self.connect()
        try:
            await self._client.delete_collection(self._collection)
            logger.info("qdrant_collection_deleted", name=self._collection)
            # Recreate the collection
            await self._client.create_collection(
                collection_name=self._collection,
                vectors_config=VectorParams(
                    size=self._dimension,
                    distance=Distance.COSINE,
                ),
            )
            logger.info("qdrant_collection_recreated", name=self._collection)
        except Exception as e:
            logger.error("failed_clearing_qdrant", error=str(e))


_retrieval_memory: RetrievalMemory | None = None


def get_retrieval_memory() -> RetrievalMemory:
    global _retrieval_memory
    if _retrieval_memory is None:
        _retrieval_memory = RetrievalMemory()
    return _retrieval_memory
