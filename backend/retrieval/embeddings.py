"""
Embedding Service
Local sentence-transformers embeddings (runs on CPU, no API key needed).
Falls back gracefully if GPU not available.
"""

import structlog
import numpy as np
from functools import lru_cache

logger = structlog.get_logger()

_model = None


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        from config.settings import get_settings

        settings = get_settings()
        _model = SentenceTransformer(settings.embedding_model)
        logger.info("embedding_model_loaded", model=settings.embedding_model)
    return _model


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """Generate embeddings for a list of texts."""
    if not texts:
        return []

    model = _get_model()
    embeddings = model.encode(texts, show_progress_bar=False, normalize_embeddings=True)
    return embeddings.tolist()


async def embed_query(query: str) -> list[float]:
    """Generate embedding for a single query."""
    results = await embed_texts([query])
    return results[0] if results else []


def embed_query_sync(query: str) -> list[float]:
    """Generate embedding for a single query synchronously."""
    model = _get_model()
    embeddings = model.encode([query], show_progress_bar=False, normalize_embeddings=True)
    return embeddings[0].tolist() if len(embeddings) > 0 else []


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    a_np = np.array(a)
    b_np = np.array(b)
    return float(np.dot(a_np, b_np) / (np.linalg.norm(a_np) * np.linalg.norm(b_np) + 1e-8))
