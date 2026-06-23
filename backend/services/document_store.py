"""
Document Store Service
Ingestion pipeline for web pages and PDFs with URL and content deduplication.
"""

import hashlib
from urllib.parse import urlparse

import structlog

from schemas.agents import BrowsedPage, ReadDocument

logger = structlog.get_logger()


class DocumentStore:
    """Manages document ingestion and deduplication."""

    def __init__(self):
        self._documents: dict[str, ReadDocument] = {}

    def content_hash(self, content: str) -> str:
        """Generate SHA-256 hash for deduplication."""
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def store_document(self, doc: ReadDocument) -> str:
        """Store a document, return hash key."""
        key = self.content_hash(doc.summary)
        self._documents[key] = doc
        return key

    def get_document(self, key: str) -> ReadDocument | None:
        return self._documents.get(key)

    def get_all_documents(self) -> list[ReadDocument]:
        return list(self._documents.values())

    @staticmethod
    def normalize_url(url: str) -> str:
        """Normalize URL for deduplication."""
        try:
            parsed = urlparse(url)
            path = parsed.path.rstrip("/")
            return f"{parsed.scheme}://{parsed.netloc}{path}"
        except Exception:
            return url

    def deduplicate_pages(self, pages: list[BrowsedPage]) -> list[BrowsedPage]:
        """Remove duplicate pages based on URL and content hash."""
        seen_urls: set[str] = set()
        seen_hashes: set[str] = set()
        unique: list[BrowsedPage] = []

        for page in pages:
            norm_url = self.normalize_url(page.url)
            if norm_url in seen_urls:
                continue
            seen_urls.add(norm_url)

            if page.word_count > 0:
                h = self.content_hash(page.content[:500])
                if h in seen_hashes:
                    continue
                seen_hashes.add(h)

            unique.append(page)

        return unique


_doc_store: DocumentStore | None = None


def get_document_store() -> DocumentStore:
    global _doc_store
    if _doc_store is None:
        _doc_store = DocumentStore()
    return _doc_store
