# Wikipedia Tool — fetches article summaries and introductory sections via the Wikipedia API.

import asyncio
import urllib.parse

import aiohttp

from backend.tools.base_tool import BaseTool, ToolResult
from backend.utils.logger import get_logger

logger = get_logger(__name__)

WIKIPEDIA_API = "https://en.wikipedia.org/w/api.php"
WIKIPEDIA_BASE = "https://en.wikipedia.org/wiki/"


class WikipediaTool(BaseTool):
    """Wikipedia search + article extraction. No API key required."""

    name = "wikipedia"
    description = "Search Wikipedia for encyclopedic background information."

    async def run(self, query: str, max_results: int = 3) -> list[ToolResult]:
        logger.info(f"[WikipediaTool] Searching: {query!r}")
        try:
            # Step 1: Search for matching article titles
            titles = await self._search_titles(query, limit=max_results)
            if not titles:
                logger.warning(f"[WikipediaTool] No articles found for: {query!r}")
                return []

            # Step 2: Fetch summary for each title concurrently
            tasks = [self._fetch_summary(title, query) for title in titles]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            good_results = [r for r in results if isinstance(r, ToolResult) and not r.error]
            logger.info(f"[WikipediaTool] Got {len(good_results)} articles for: {query!r}")
            return good_results

        except Exception as exc:
            logger.error(f"[WikipediaTool] Error for {query!r}: {exc}")
            return [ToolResult(
                tool=self.name, query=query,
                title="[Error] Wikipedia lookup failed",
                content="", url="", error=str(exc)
            )]

    _HEADERS = {
        "User-Agent": "AutonomousResearchAgent/1.0 (https://github.com/autonomous-research-agent; contact@example.com)",
        "Accept": "application/json",
    }

    async def _search_titles(self, query: str, limit: int) -> list[str]:
        params = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "srlimit": limit,
            "format": "json",
            "utf8": 1,
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(
                WIKIPEDIA_API,
                params=params,
                timeout=aiohttp.ClientTimeout(total=15),
                headers=self._HEADERS,
            ) as resp:
                resp.raise_for_status()
                data = await resp.json(content_type=None)
                return [item["title"] for item in data.get("query", {}).get("search", [])]

    async def _fetch_summary(self, title: str, query: str) -> ToolResult:
        params = {
            "action": "query",
            "titles": title,
            "prop": "extracts",
            "exintro": 1,             # Only intro section (must be int, not bool — yarl compat)
            "explaintext": 1,         # Plain text, no HTML
            "exsectionformat": "plain",
            "format": "json",
            "utf8": 1,
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(
                WIKIPEDIA_API,
                params=params,
                timeout=aiohttp.ClientTimeout(total=15),
                headers=self._HEADERS,
            ) as resp:
                resp.raise_for_status()
                data = await resp.json(content_type=None)

        pages = data.get("query", {}).get("pages", {})
        page = next(iter(pages.values()))

        extract = page.get("extract", "").strip()
        if not extract:
            return ToolResult(
                tool=self.name, query=query,
                title=title, content="", url="",
                error="Empty extract"
            )

        # Truncate very long intros to ~2000 chars
        if len(extract) > 2000:
            extract = extract[:2000].rsplit(" ", 1)[0] + "..."

        url = WIKIPEDIA_BASE + urllib.parse.quote(title.replace(" ", "_"))
        return ToolResult(
            tool=self.name,
            query=query,
            title=title,
            content=extract,
            url=url,
            source_type="wikipedia",
            relevance_score=0.85,
        )
