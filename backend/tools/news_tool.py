# News Tool — fetches recent news articles via Tavily in "news" search mode.

import asyncio

from backend.tools.base_tool import BaseTool, ToolResult
from backend.utils.config import settings
from backend.utils.logger import get_logger

logger = get_logger(__name__)


class NewsTool(BaseTool):
    """Fetch recent news articles related to the query using Tavily news mode."""

    name = "news"
    description = "Search for recent news articles and current events on a topic."

    def __init__(self) -> None:
        try:
            from tavily import TavilyClient
            self._client = TavilyClient(api_key=settings.tavily_api_key)
            logger.info("[NewsTool] Tavily client initialized")
        except Exception as exc:
            logger.warning(f"[NewsTool] Failed to init Tavily client: {exc}")
            self._client = None

    async def run(self, query: str, max_results: int = 5) -> list[ToolResult]:
        if not self._client:
            return [ToolResult(
                tool=self.name, query=query,
                title="[Error] News client unavailable",
                content="", url="", error="Tavily client not initialized"
            )]

        try:
            logger.info(f"[NewsTool] Searching news for: {query!r}")
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self._client.search(
                    query=query,
                    max_results=max_results,
                    search_depth="basic",
                    topic="news",                # Tavily news mode
                    include_answer=False,
                )
            )

            results: list[ToolResult] = []
            for item in response.get("results", []):
                content = item.get("content", "").strip()
                if not content:
                    continue
                results.append(ToolResult(
                    tool=self.name,
                    query=query,
                    title=item.get("title", "Untitled News Article"),
                    content=content,
                    url=item.get("url", ""),
                    source_type="news",
                    relevance_score=float(item.get("score", 0.5)),
                ))

            logger.info(f"[NewsTool] Got {len(results)} news items for: {query!r}")
            return results

        except Exception as exc:
            logger.error(f"[NewsTool] Failed for {query!r}: {exc}")
            return [ToolResult(
                tool=self.name, query=query,
                title="[Error] News search failed",
                content="", url="", error=str(exc)
            )]
