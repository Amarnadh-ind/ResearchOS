"""
Firecrawl Service
Web content extraction via Firecrawl SDK with automatic fallback to httpx + BeautifulSoup.
"""

import asyncio

import structlog
from bs4 import BeautifulSoup
from markdownify import markdownify as md

from config.settings import get_settings
from schemas.agents import BrowsedPage

logger = structlog.get_logger()

FALLBACK_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)


class FirecrawlService:
    """Web content extraction via Firecrawl SDK with fallback mechanisms."""

    def __init__(self):
        self.settings = get_settings()
        self._api_key = self.settings.firecrawl_api_key
        self._base_url = self.settings.firecrawl_base_url
        self._client = None
        self._http_client = None

        # Redis cache configuration
        self._redis_url = self.settings.redis_url
        self._redis_client = None
        self._in_memory_cache = {}

        # Diagnostics metrics
        self.firecrawl_requests = 0
        self.firecrawl_success = 0
        self.firecrawl_failed = 0
        self.firecrawl_latency_ms = 0

        # Provider Card info
        self.status = "online" if self.available else "offline"
        self.last_latency = 0
        self.last_error = ""

    @property
    def available(self) -> bool:
        return bool(self._api_key)

    async def _ensure_redis(self):
        if self._redis_client is None:
            try:
                import redis.asyncio as redis

                self._redis_client = redis.from_url(self._redis_url, decode_responses=True)
                await self._redis_client.ping()
            except Exception as e:
                logger.warning("redis_unavailable_for_firecrawl_cache", error=str(e))
                self._redis_client = "in_memory"

    async def get_cached_page(self, url: str) -> BrowsedPage | None:
        """Retrieve a cached page from Redis or in-memory cache."""
        import hashlib
        import json

        cache_key = hashlib.sha256(url.encode()).hexdigest()
        redis_key = f"ros:firecrawl:cache:{cache_key}"

        await self._ensure_redis()
        cached_data = None
        if self._redis_client == "in_memory":
            cached_data = self._in_memory_cache.get(cache_key)
        elif self._redis_client is not None:
            try:
                cached_data = await self._redis_client.get(redis_key)
            except Exception as e:
                logger.warning("failed_reading_firecrawl_cache", error=str(e))

        if cached_data:
            try:
                data = json.loads(cached_data)
                # Support both set of keys (old & new)
                content = data.get("markdown") or data.get("content") or ""
                source_url = data.get("source_url") or data.get("url") or url
                title = data.get("title") or url
                metadata = data.get("metadata") or {}

                return BrowsedPage(
                    url=source_url,
                    title=title,
                    content=content,
                    content_type=data.get("content_type", "markdown"),
                    word_count=data.get("word_count", len(content.split())),
                    extraction_quality=data.get("extraction_quality", 0.8),
                    publication_date=metadata.get("publication_date") or "",
                    author=metadata.get("author") or "",
                    site_name=metadata.get("site_name") or "",
                    description=metadata.get("description") or "",
                )
            except Exception as e:
                logger.warning("failed_deserializing_cached_page", error=str(e))
        return None

    async def cache_page(self, url: str, page: BrowsedPage):
        """Cache a successfully scraped page."""
        if page.content_type == "error" or page.word_count <= 20:
            return

        import hashlib
        import json

        cache_key = hashlib.sha256(url.encode()).hexdigest()
        redis_key = f"ros:firecrawl:cache:{cache_key}"

        cache_val = {
            "title": page.title,
            "markdown": page.content,
            "content": page.content,
            "metadata": {
                "description": page.description or "",
                "site_name": page.site_name or "",
                "author": page.author or "",
                "publication_date": page.publication_date or "",
            },
            "source_url": page.url,
            "url": page.url,
            "word_count": page.word_count,
            "extraction_quality": page.extraction_quality,
            "content_type": page.content_type,
        }

        await self._ensure_redis()
        if self._redis_client == "in_memory":
            self._in_memory_cache[cache_key] = json.dumps(cache_val)
        elif self._redis_client is not None:
            try:
                await self._redis_client.set(redis_key, json.dumps(cache_val), ex=86400)
            except Exception as e:
                logger.warning("failed_writing_firecrawl_cache", error=str(e))

    def _ensure_sdk_client(self):
        if self._client is None:
            from firecrawl import Firecrawl

            self._client = Firecrawl(api_key=self._api_key, base_url=self._base_url)

    async def _ensure_http_client(self):
        if self._http_client is None:
            import httpx

            self._http_client = httpx.AsyncClient(
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                timeout=httpx.Timeout(60.0, connect=15.0),
            )

    async def close(self):
        self._client = None
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()
            self._http_client = None

    async def scrape(self, url: str, timeout: int | None = None) -> BrowsedPage:
        """Scrape a URL via Firecrawl SDK with fallback to httpx+BeautifulSoup and caching.

        Returns a BrowsedPage with extracted content, title, and metadata.
        """
        from config.settings import get_settings

        _settings = get_settings()
        if timeout is None:
            timeout = _settings.fast_mode_firecrawl_timeout if _settings.fast_mode else 30000

        cached_page = await self.get_cached_page(url)
        if cached_page:
            logger.info("firecrawl_cache_hit", url=url)
            return cached_page

        if self.available:
            import time

            self.firecrawl_requests += 1
            start_time = time.monotonic()
            try:
                page = await self._scrape_via_sdk(url, timeout)
                latency_ms = int((time.monotonic() - start_time) * 1000)
                self.firecrawl_success += 1
                self.firecrawl_latency_ms = latency_ms
                self.last_latency = latency_ms
                self.status = "online"
                self.last_error = ""
                # Cache the successful page
                await self.cache_page(url, page)
                return page
            except Exception as e:
                latency_ms = int((time.monotonic() - start_time) * 1000)
                self.firecrawl_failed += 1
                self.firecrawl_latency_ms = latency_ms
                self.last_latency = latency_ms
                self.status = "offline"
                self.last_error = str(e)
                logger.warning("firecrawl_sdk_scrape_failed_falling_back", url=url, error=str(e))

        # 3. Fallback Scraper (BeautifulSoup/httpx)
        page = await self._scrape_via_httpx(url, timeout)
        # Cache successful fallback results
        if page.content_type != "error" and page.word_count > 20:
            await self.cache_page(url, page)
        return page

    async def batch_scrape(self, urls: list[str], timeout: int = 30000) -> list[BrowsedPage]:
        """Scrape multiple URLs checking cache first, batching uncached ones if >=3."""
        pages = []
        uncached_urls = []
        url_to_page = {}

        # 1. Check cache for all URLs
        for url in urls:
            cached_page = await self.get_cached_page(url)
            if cached_page:
                logger.info("firecrawl_cache_hit", url=url)
                url_to_page[url] = cached_page
            else:
                uncached_urls.append(url)

        # 2. If there are uncached URLs, scrape them
        if uncached_urls:
            # If batching is available and we have >= 3 uncached URLs, batch scrape them
            if self.available and len(uncached_urls) >= 3:
                import time

                self.firecrawl_requests += 1
                start_time = time.monotonic()
                try:
                    scraped_pages = await self._batch_scrape_via_sdk(uncached_urls, timeout)
                    latency_ms = int((time.monotonic() - start_time) * 1000)
                    self.firecrawl_success += 1
                    self.firecrawl_latency_ms = latency_ms
                    self.last_latency = latency_ms
                    self.status = "online"
                    self.last_error = ""

                    for p in scraped_pages:
                        url_to_page[p.url] = p
                        # Cache the successful page
                        await self.cache_page(p.url, p)

                    # Any uncached URL that wasn't returned by batch scrape is considered failed/missing
                    for url in uncached_urls:
                        if url not in url_to_page:
                            # Fallback sequentially
                            p = await self.scrape(url, timeout)
                            url_to_page[url] = p

                except Exception as e:
                    latency_ms = int((time.monotonic() - start_time) * 1000)
                    self.firecrawl_failed += 1
                    self.firecrawl_latency_ms = latency_ms
                    self.last_latency = latency_ms
                    self.status = "offline"
                    self.last_error = str(e)
                    logger.warning("firecrawl_sdk_batch_failed_falling_back", error=str(e))

                    # Fallback sequentially for all uncached
                    for url in uncached_urls:
                        p = await self.scrape(url, timeout)
                        url_to_page[url] = p
            else:
                # Scrape sequentially
                for url in uncached_urls:
                    p = await self.scrape(url, timeout)
                    url_to_page[url] = p

        # 3. Assemble pages in original order
        for url in urls:
            if url in url_to_page:
                pages.append(url_to_page[url])

        return pages

    async def extract_markdown(self, url: str, timeout: int = 30000) -> str | None:
        """Extract clean markdown from a URL."""
        page = await self.scrape(url, timeout)
        if page.word_count > 20:
            return page.content
        return None

    async def _scrape_via_sdk(self, url: str, timeout: int) -> BrowsedPage:
        """Scrape using the Firecrawl SDK."""
        self._ensure_sdk_client()

        def _do_scrape():
            return self._client.scrape(
                url,
                params={
                    "formats": ["markdown", "metadata"],
                    "onlyMainContent": True,
                    "timeout": timeout,
                },
            )

        result = await asyncio.to_thread(_do_scrape)

        if not result:
            raise ValueError("Firecrawl SDK returned no result")

        if isinstance(result, dict):
            data = result
        else:
            data = result if hasattr(result, "get") else {}

        markdown = data.get("markdown", "") or data.get("content", "")
        metadata = data.get("metadata", {}) or {}

        title = metadata.get("title", "") or metadata.get("ogTitle", "") or url
        description = metadata.get("description", "") or metadata.get("ogDescription", "")
        publication_date = metadata.get("publishedDate") or metadata.get("date") or None
        author = metadata.get("author") or metadata.get("byline") or None
        site_name = metadata.get("sourceURL") or metadata.get("url") or url

        word_count = len(markdown.split())
        quality = self._compute_quality(markdown, metadata)

        logger.info("firecrawl_sdk_scrape_success", url=url, words=word_count, quality=quality)

        return BrowsedPage(
            url=url,
            title=title or url,
            content=markdown,
            content_type="markdown",
            word_count=word_count,
            extraction_quality=quality,
            publication_date=publication_date or "",
            author=author or "",
            site_name=site_name or "",
            description=description or "",
        )

    async def _batch_scrape_via_sdk(self, urls: list[str], timeout: int) -> list[BrowsedPage]:
        """Scrape multiple URLs using the Firecrawl SDK batch endpoint."""
        self._ensure_sdk_client()

        def _do_batch_scrape():
            return self._client.batch_scrape_urls(
                urls,
                params={
                    "formats": ["markdown", "metadata"],
                    "onlyMainContent": True,
                    "timeout": timeout,
                },
            )

        results_data = await asyncio.to_thread(_do_batch_scrape)

        results = []
        for item in (
            results_data if isinstance(results_data, list) else results_data.get("data", [])
        ):
            if isinstance(item, dict):
                data = item
            else:
                data = item if hasattr(item, "get") else {}

            markdown = data.get("markdown", "") or data.get("content", "")
            metadata = data.get("metadata", {}) or {}
            page_url = metadata.get("sourceURL", "") or data.get("url", "")
            title = metadata.get("title", "") or metadata.get("ogTitle", "") or page_url
            description = metadata.get("description", "") or metadata.get("ogDescription", "")
            publication_date = metadata.get("publishedDate") or metadata.get("date") or None
            author = metadata.get("author") or metadata.get("byline") or None
            site_name = metadata.get("sourceURL") or metadata.get("url") or page_url
            word_count = len(markdown.split())
            quality = self._compute_quality(markdown, metadata)

            results.append(
                BrowsedPage(
                    url=page_url,
                    title=title or page_url,
                    content=markdown,
                    content_type="markdown",
                    word_count=word_count,
                    extraction_quality=quality,
                    publication_date=publication_date or "",
                    author=author or "",
                    site_name=site_name or "",
                    description=description or "",
                )
            )

        logger.info("firecrawl_sdk_batch_success", requested=len(urls), received=len(results))
        return results

    async def _scrape_via_httpx(self, url: str, timeout: int) -> BrowsedPage:
        """Fallback scraper using raw httpx + BeautifulSoup."""
        import httpx

        headers = {
            "User-Agent": FALLBACK_USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }

        try:
            async with httpx.AsyncClient(
                headers=headers,
                follow_redirects=True,
                timeout=httpx.Timeout(timeout / 1000, connect=10.0),
            ) as client:
                response = await client.get(url)
                response.raise_for_status()

                content_type = response.headers.get("content-type", "").lower()
                if "application/pdf" in content_type or url.lower().endswith(".pdf"):
                    from services.pdf_parser import get_pdf_parser

                    parser = get_pdf_parser()
                    parsed = await parser.parse_pdf(response.content)
                    title = parsed.get("title") or url
                    text = parsed.get("full_text") or ""
                    word_count = len(text.split())
                    quality = min(1.0, word_count / 500) if word_count > 0 else 0.0
                    return BrowsedPage(
                        url=url,
                        title=title or url,
                        content=text,
                        content_type="pdf",
                        word_count=word_count,
                        extraction_quality=quality,
                        publication_date="",
                        author="",
                        site_name="",
                        description="",
                    )

                html = response.text
                soup = BeautifulSoup(html, "lxml")
                title_tag = soup.find("title")
                title = title_tag.get_text(strip=True) if title_tag else url
                content = self._extract_content_fallback(html)
                word_count = len(content.split())
                quality = min(1.0, word_count / 500) if word_count > 0 else 0.0

                return BrowsedPage(
                    url=url,
                    title=title or url,
                    content=content,
                    content_type="text",
                    word_count=word_count,
                    extraction_quality=quality,
                    publication_date="",
                    author="",
                    site_name="",
                    description="",
                )

        except Exception as e:
            logger.error("fallback_scrape_error", url=url, error=str(e))
            return BrowsedPage(
                url=url,
                title=url,
                content=f"Error extracting content: {str(e)}",
                content_type="error",
                word_count=0,
                extraction_quality=0.0,
                publication_date="",
                author="",
                site_name="",
                description="",
            )

    def _extract_content_fallback(self, html: str) -> str:
        """Extract readable content from HTML (fallback path)."""
        soup = BeautifulSoup(html, "lxml")
        for tag in soup.find_all(
            ["script", "style", "nav", "header", "footer", "aside", "iframe", "noscript"]
        ):
            tag.decompose()

        main = (
            soup.find("main")
            or soup.find("article")
            or soup.find(attrs={"role": "main"})
            or soup.find("div", class_=lambda c: c and "content" in str(c).lower())
        )
        target = main if main else soup.body if soup.body else soup
        content = md(str(target), strip=["img", "a"], heading_style="ATX")
        lines = [line.strip() for line in content.split("\n") if line.strip()]
        result = "\n\n".join(lines)
        if len(result) > 50000:
            result = result[:50000] + "\n\n[Content truncated]"
        return result

    @staticmethod
    def _compute_quality(markdown: str, metadata: dict) -> float:
        """Compute extraction quality score based on content signals."""
        word_count = len(markdown.split())
        if word_count == 0:
            return 0.0

        has_title = bool(metadata.get("title") or metadata.get("ogTitle"))
        has_description = bool(metadata.get("description") or metadata.get("ogDescription"))
        has_date = bool(metadata.get("publishedDate") or metadata.get("date"))

        score = 0.0
        if word_count > 2000:
            score += 0.4
        elif word_count > 500:
            score += 0.3
        elif word_count > 100:
            score += 0.15
        else:
            score += 0.05

        if has_title:
            score += 0.2
        if has_description:
            score += 0.15
        if has_date:
            score += 0.15
        if word_count > 100:
            score += 0.1

        return min(1.0, score)

    async def _health_check(self) -> bool:
        """Check if Firecrawl API is reachable via SDK health endpoint."""
        if not self.available:
            return False
        try:
            self._ensure_sdk_client()

            def _do_health():
                return self._client._request("GET", f"{self._base_url}/health")

            await asyncio.to_thread(_do_health)
            return True
        except Exception:
            return False


_firecrawl_service: FirecrawlService | None = None


def get_firecrawl_service() -> FirecrawlService:
    global _firecrawl_service
    if _firecrawl_service is None:
        _firecrawl_service = FirecrawlService()
    return _firecrawl_service
