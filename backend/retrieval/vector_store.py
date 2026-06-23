"""
Vector Store operations for Qdrant.
"""

import structlog

from memory.retrieval_mem import get_retrieval_memory
from retrieval.embeddings import embed_query, embed_texts

logger = structlog.get_logger()


class VectorStore:
    """High-level vector store operations."""

    def __init__(self):
        self._memory = get_retrieval_memory()

    async def index_documents(
        self,
        texts: list[str],
        metadatas: list[dict],
        chunk_size: int = 512,
    ):
        """Chunk, embed, and index documents."""
        chunks = []
        chunk_metas = []

        for text, meta in zip(texts, metadatas):
            # Simple chunking by paragraphs then by size
            paragraphs = text.split("\n\n")
            current_chunk = ""

            for para in paragraphs:
                if len(current_chunk) + len(para) > chunk_size:
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                        chunk_metas.append(meta)
                    current_chunk = para
                else:
                    current_chunk += "\n\n" + para

            if current_chunk.strip():
                chunks.append(current_chunk.strip())
                chunk_metas.append(meta)

        if not chunks:
            return

        # Generate embeddings
        embeddings = await embed_texts(chunks)

        # Store in Qdrant
        await self._memory.upsert_documents(chunks, embeddings, chunk_metas)
        logger.info("documents_indexed", chunks=len(chunks))

    async def search(
        self,
        query: str,
        limit: int = 10,
        session_id: str | None = None,
    ) -> list[dict]:
        """Semantic search."""
        query_emb = await embed_query(query)
        return await self._memory.search(query_emb, limit=limit, session_id=session_id)


_vector_store: VectorStore | None = None


def get_vector_store() -> VectorStore:
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store
