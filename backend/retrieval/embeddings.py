"""
Embedding Service
Local sentence-transformers embeddings (runs on CPU, no API key needed).
Falls back gracefully if GPU not available.
Includes LRU cache to avoid re-embedding duplicate texts between stages.
"""

import hashlib
from collections import OrderedDict

import numpy as np
import structlog

logger = structlog.get_logger()

_model = None

# ── Embedding result cache: key = sha256(text) → embedding list ──
_embedding_cache: OrderedDict[str, list[float]] = OrderedDict()
_MAX_CACHE_SIZE = 2048


def _cache_key(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


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
    """Generate embeddings for a list of texts (with cache)."""
    if not texts:
        return []

    results: list[list[float] | None] = [None] * len(texts)
    missing_indices: list[int] = []
    missing_texts: list[str] = []

    for i, t in enumerate(texts):
        key = _cache_key(t)
        if key in _embedding_cache:
            results[i] = _embedding_cache[key]
        else:
            missing_indices.append(i)
            missing_texts.append(t)

    if missing_texts:
        model = _get_model()
        new_embs = model.encode(missing_texts, show_progress_bar=False, normalize_embeddings=True)
        for idx, emb in zip(missing_indices, new_embs):
            emb_list = emb.tolist()
            results[idx] = emb_list
            key = _cache_key(texts[idx])
            _embedding_cache[key] = emb_list
            if len(_embedding_cache) > _MAX_CACHE_SIZE:
                _embedding_cache.popitem(last=False)

    return [r for r in results if r is not None]


async def embed_query(query: str) -> list[float]:
    """Generate embedding for a single query (with cache)."""
    key = _cache_key(query)
    if key in _embedding_cache:
        return _embedding_cache[key]
    model = _get_model()
    emb = model.encode([query], show_progress_bar=False, normalize_embeddings=True)
    emb_list = emb[0].tolist()
    _embedding_cache[key] = emb_list
    if len(_embedding_cache) > _MAX_CACHE_SIZE:
        _embedding_cache.popitem(last=False)
    return emb_list


def embed_query_sync(query: str) -> list[float]:
    """Generate embedding for a single query synchronously (with cache)."""
    key = _cache_key(query)
    if key in _embedding_cache:
        return _embedding_cache[key]
    model = _get_model()
    embeddings = model.encode([query], show_progress_bar=False, normalize_embeddings=True)
    emb_list = embeddings[0].tolist() if len(embeddings) > 0 else []
    _embedding_cache[key] = emb_list
    if len(_embedding_cache) > _MAX_CACHE_SIZE:
        _embedding_cache.popitem(last=False)
    return emb_list


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    a_np = np.array(a)
    b_np = np.array(b)
    return float(np.dot(a_np, b_np) / (np.linalg.norm(a_np) * np.linalg.norm(b_np) + 1e-8))
