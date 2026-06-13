"""
BM25 Keyword Retrieval
Sparse retrieval for keyword-based search.
"""

import math
import structlog
from collections import Counter

logger = structlog.get_logger()


class BM25Retriever:
    """BM25-based keyword retrieval over documents."""

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self._documents: list[dict] = []  # {text, metadata}
        self._tokenized: list[list[str]] = []
        self._doc_freqs: Counter = Counter()
        self._avg_dl: float = 0

    def _tokenize(self, text: str) -> list[str]:
        """Simple whitespace + lowercase tokenization."""
        return [w.lower().strip(".,!?;:\"'()[]{}") for w in text.split() if len(w) > 2]

    def index(self, documents: list[dict]):
        """Index documents for BM25 retrieval."""
        self._documents = documents
        self._tokenized = []
        self._doc_freqs = Counter()

        for doc in documents:
            tokens = self._tokenize(doc.get("text", ""))
            self._tokenized.append(tokens)
            unique_tokens = set(tokens)
            for token in unique_tokens:
                self._doc_freqs[token] += 1

        total_len = sum(len(t) for t in self._tokenized)
        self._avg_dl = total_len / len(self._tokenized) if self._tokenized else 1

        logger.info("bm25_indexed", documents=len(documents))

    def search(self, query: str, limit: int = 10) -> list[dict]:
        """Search indexed documents using BM25."""
        if not self._documents:
            return []

        query_tokens = self._tokenize(query)
        n = len(self._documents)
        scores: list[tuple[int, float]] = []

        for i, doc_tokens in enumerate(self._tokenized):
            score = 0.0
            dl = len(doc_tokens)
            tf_map = Counter(doc_tokens)

            for qt in query_tokens:
                tf = tf_map.get(qt, 0)
                if tf == 0:
                    continue
                df = self._doc_freqs.get(qt, 0)
                idf = math.log((n - df + 0.5) / (df + 0.5) + 1)
                numerator = tf * (self.k1 + 1)
                denominator = tf + self.k1 * (1 - self.b + self.b * dl / self._avg_dl)
                score += idf * numerator / denominator

            if score > 0:
                scores.append((i, score))

        scores.sort(key=lambda x: x[1], reverse=True)

        results = []
        for idx, score in scores[:limit]:
            doc = self._documents[idx].copy()
            doc["bm25_score"] = score
            results.append(doc)

        return results


_bm25: BM25Retriever | None = None


def get_bm25_retriever() -> BM25Retriever:
    global _bm25
    if _bm25 is None:
        _bm25 = BM25Retriever()
    return _bm25
