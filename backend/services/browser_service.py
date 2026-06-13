"""
Browser Service
HTTP-based web scraping with content extraction.
Uses httpx + BeautifulSoup instead of Playwright to avoid subprocess issues on Windows.
"""

import structlog
import httpx
from bs4 import BeautifulSoup
from markdownify import markdownify as md

from schemas.agents import BrowsedPage

logger = structlog.get_logger()

# Standard browser user agent
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)


class BrowserService:
    """HTTP-based web content extraction (no Playwright dependency)."""

    def __init__(self):
        self._client: httpx.AsyncClient | None = None

    async def start(self):
        """Create the HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                headers={
                    "User-Agent": USER_AGENT,
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Accept-Encoding": "gzip, deflate, br",
                },
                follow_redirects=True,
                timeout=httpx.Timeout(30.0, connect=10.0),
                limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
            )
            logger.info("browser_http_client_started")

    async def stop(self):
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def browse_page(self, url: str, timeout: int = 30000) -> BrowsedPage:
        """Browse a URL and extract content using httpx."""
        await self.start()

        try:
            response = await self._client.get(url)
            response.raise_for_status()

            # Check if it is a PDF
            content_type = response.headers.get("content-type", "").lower()
            is_pdf = "application/pdf" in content_type or url.lower().endswith(".pdf")

            if is_pdf:
                from services.pdf_parser import get_pdf_parser
                parser = get_pdf_parser()
                parsed = await parser.parse_pdf(response.content)
                title = parsed.get("title") or url
                content = parsed.get("full_text") or ""
                word_count = len(content.split())
                quality = min(1.0, word_count / 500) if word_count > 0 else 0.0

                logger.info("pdf_page_browsed", url=url, words=word_count)

                return BrowsedPage(
                    url=url,
                    title=title or url,
                    content=content,
                    content_type="pdf",
                    word_count=word_count,
                    extraction_quality=quality,
                )

            html = response.text

            # Get page title
            soup = BeautifulSoup(html, "lxml")
            title_tag = soup.find("title")
            title = title_tag.get_text(strip=True) if title_tag else url

            # Extract main content
            content = self._extract_content(html)
            word_count = len(content.split())
            quality = min(1.0, word_count / 500) if word_count > 0 else 0.0

            logger.info("page_browsed", url=url, words=word_count)

            return BrowsedPage(
                url=url,
                title=title or url,
                content=content,
                content_type="text",
                word_count=word_count,
                extraction_quality=quality,
            )

        except Exception as e:
            logger.error("browse_error", url=url, error=str(e))
            return BrowsedPage(
                url=url,
                title=url,
                content=f"Error extracting content: {str(e)}",
                content_type="error",
                word_count=0,
                extraction_quality=0.0,
            )

    def _extract_content(self, html: str) -> str:
        """Extract readable content from HTML."""
        soup = BeautifulSoup(html, "lxml")

        # Remove non-content elements
        for tag in soup.find_all(
            ["script", "style", "nav", "header", "footer", "aside", "iframe", "noscript"]
        ):
            tag.decompose()

        # Try to find main content
        main = (
            soup.find("main")
            or soup.find("article")
            or soup.find(attrs={"role": "main"})
            or soup.find("div", class_=lambda c: c and "content" in str(c).lower())
        )

        target = main if main else soup.body if soup.body else soup

        # Convert to markdown
        content = md(str(target), strip=["img", "a"], heading_style="ATX")

        # Clean up excessive whitespace
        lines = [line.strip() for line in content.split("\n")]
        lines = [line for line in lines if line]

        # Truncate overly long pages to prevent memory issues
        result = "\n\n".join(lines)
        if len(result) > 50000:
            result = result[:50000] + "\n\n[Content truncated]"

        return result

    async def browse_multiple(self, urls: list[str]) -> list[BrowsedPage]:
        """Browse multiple URLs concurrently."""
        import asyncio

        # Browse in batches of 5 for controlled concurrency
        pages = []
        batch_size = 5
        for i in range(0, len(urls), batch_size):
            batch = urls[i : i + batch_size]
            batch_results = await asyncio.gather(
                *[self.browse_page(url) for url in batch],
                return_exceptions=True,
            )
            for j, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    pages.append(
                        BrowsedPage(
                            url=batch[j],
                            title=batch[j],
                            content=f"Error: {str(result)}",
                            content_type="error",
                            word_count=0,
                            extraction_quality=0.0,
                        )
                    )
                else:
                    pages.append(result)
        return pages


_browser_service: BrowserService | None = None


def get_browser_service() -> BrowserService:
    global _browser_service
    if _browser_service is None:
        _browser_service = BrowserService()
    return _browser_service
