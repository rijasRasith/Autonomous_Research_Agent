# Documentation Tool — scrapes documentation sites and technical pages using BeautifulSoup + aiohttp.
# Falls back gracefully when Playwright is unavailable.

import re

import aiohttp
from bs4 import BeautifulSoup

from backend.tools.base_tool import BaseTool, ToolResult
from backend.utils.logger import get_logger

logger = get_logger(__name__)


CONTENT_TAGS = ["article", "main", "section", ".content", "#content", "div[role='main']"]

# Tags to strip (nav, sidebars, headers, footers, ads)
STRIP_TAGS = [
    "nav", "header", "footer", "aside", "script", "style",
    "noscript", "iframe", "form", "button", "svg", "img",
    ".nav", ".navbar", ".sidebar", ".menu", ".ad", ".cookie",
    ".breadcrumb", ".pagination",
]


class DocumentationTool(BaseTool):
    """Scrape documentation pages and technical articles with BeautifulSoup."""

    name = "documentation"
    description = "Scrape documentation pages, technical blogs, and reference material."

    async def run(self, query: str, max_results: int = 3) -> list[ToolResult]:
        """
        For documentation tool we use Tavily to discover the best doc URLs,
        then scrape the top pages for their full text — deeper than a snippet.
        """
        logger.info(f"[DocumentationTool] Finding docs for: {query!r}")
        try:
            urls = await self._discover_urls(query, max_results)
            if not urls:
                return []

            import asyncio
            tasks = [self._scrape(url, query) for url in urls]
            raw = await asyncio.gather(*tasks, return_exceptions=True)
            results = [r for r in raw if isinstance(r, ToolResult) and r.content and not r.error]
            logger.info(f"[DocumentationTool] Scraped {len(results)} pages for: {query!r}")
            return results
        except Exception as exc:
            logger.error(f"[DocumentationTool] Error for {query!r}: {exc}")
            return [ToolResult(
                tool=self.name, query=query,
                title="[Error] Documentation scraping failed",
                content="", url="", error=str(exc)
            )]

    async def _discover_urls(self, query: str, limit: int) -> list[str]:
        """Use Tavily search to find the best documentation URLs."""
        try:
            from backend.utils.config import settings
            from tavily import TavilyClient
            import asyncio
            client = TavilyClient(api_key=settings.tavily_api_key)
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: client.search(
                    query=f"{query} documentation official site",
                    max_results=limit,
                    search_depth="basic",
                    include_answer=False,
                )
            )
            urls = [item["url"] for item in response.get("results", []) if item.get("url")]
            return urls[:limit]
        except Exception as exc:
            logger.warning(f"[DocumentationTool] URL discovery failed: {exc}")
            return []

    async def _scrape(self, url: str, query: str) -> ToolResult:
        """Fetch and clean one page."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    timeout=aiohttp.ClientTimeout(total=15),
                    headers={
                        "User-Agent": (
                            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/120.0.0.0 Safari/537.36"
                        ),
                        "Accept": "text/html,application/xhtml+xml",
                        "Accept-Language": "en-US,en;q=0.9",
                    },
                    allow_redirects=True,
                ) as resp:
                    if resp.status != 200:
                        return ToolResult(
                            tool=self.name, query=query,
                            title="[Error] HTTP error",
                            content="", url=url,
                            error=f"HTTP {resp.status}"
                        )
                    html = await resp.text(errors="replace")

            text, title = self._extract_text(html, url)

            if len(text) < 100:
                return ToolResult(
                    tool=self.name, query=query,
                    title=title, content="", url=url,
                    error="Insufficient content extracted"
                )

            # Truncate to 3000 chars
            if len(text) > 3000:
                text = text[:3000].rsplit(" ", 1)[0] + "..."

            return ToolResult(
                tool=self.name,
                query=query,
                title=title,
                content=text,
                url=url,
                source_type="docs",
                relevance_score=0.75,
            )

        except asyncio.TimeoutError:
            return ToolResult(
                tool=self.name, query=query,
                title="[Error] Timeout", content="", url=url, error="Timeout"
            )
        except Exception as exc:
            return ToolResult(
                tool=self.name, query=query,
                title="[Error] Scrape failed", content="", url=url, error=str(exc)
            )

    def _extract_text(self, html: str, url: str) -> tuple[str, str]:
        """Parse HTML, remove noise, return (clean_text, page_title)."""
        soup = BeautifulSoup(html, "lxml")

        # Page title
        title_tag = soup.find("title")
        title = title_tag.get_text(strip=True) if title_tag else url

        # Remove noise elements
        for selector in STRIP_TAGS:
            for tag in soup.select(selector):
                tag.decompose()

        # Try to find the main content block
        main_content = None
        for selector in ["article", "main", "[role='main']", "#content", ".content", ".doc-content"]:
            main_content = soup.select_one(selector)
            if main_content:
                break

        target = main_content if main_content else soup.find("body") or soup

        # Extract all text paragraphs
        paragraphs: list[str] = []
        for elem in target.find_all(["p", "li", "h1", "h2", "h3", "h4", "pre", "code"]):
            text = elem.get_text(separator=" ", strip=True)
            text = re.sub(r"\s+", " ", text).strip()
            if len(text) > 40:  
                paragraphs.append(text)

        return "\n\n".join(paragraphs), title


import asyncio  # noqa: E402 — needed for the timeout reference inside _scrape
