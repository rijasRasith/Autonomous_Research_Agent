# Web Search Tool — uses Tavily API for real-time web search results.

import asyncio
from typing import Optional

from backend.tools.base_tool import BaseTool, ToolResult
from backend.utils.config import settings
from backend.utils.logger import get_logger

logger = get_logger(__name__)


class WebSearchTool(BaseTool):
    """Tavily-powered web search. Returns real-time results with snippets."""

    name = "web_search"
    description = "Search the open web for current information using Tavily."

    def __init__(self) -> None:
        try:
            from tavily import TavilyClient
            self._client = TavilyClient(api_key=settings.tavily_api_key)
            logger.info("[WebSearchTool] Tavily client initialized")
        except Exception as exc:
            logger.warning(f"[WebSearchTool] Failed to init Tavily client: {exc}")
            self._client = None

    async def run(self, query: str, max_results: int = 5) -> list[ToolResult]:
        if not self._client:
            logger.error("[WebSearchTool] Tavily client not available")
            return [ToolResult(
                tool=self.name, query=query,
                title="[Error] Tavily client unavailable",
                content="", url="", error="Tavily client not initialized"
            )]

        try:
            logger.info(f"[WebSearchTool] Searching: {query!r}")

            # Run blocking Tavily call in executor so it doesn't block event loop
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self._client.search(
                    query=query,
                    max_results=max_results,
                    search_depth="advanced",
                    include_answer=True,
                    include_raw_content=False,
                )
            )

            results: list[ToolResult] = []

            # Include Tavily's synthesized answer as the first result if present
            if response.get("answer"):
                results.append(ToolResult(
                    tool=self.name,
                    query=query,
                    title="Tavily Synthesized Answer",
                    content=response["answer"],
                    url="https://tavily.com",
                    source_type="web",
                    relevance_score=1.0,
                ))

            for item in response.get("results", []):
                content = item.get("content", "").strip()
                if not content:
                    continue
                results.append(ToolResult(
                    tool=self.name,
                    query=query,
                    title=item.get("title", "Untitled"),
                    content=content,
                    url=item.get("url", ""),
                    source_type="web",
                    relevance_score=float(item.get("score", 0.5)),
                ))

            logger.info(f"[WebSearchTool] Got {len(results)} results for: {query!r}")
            return results

        except Exception as exc:
            logger.error(f"[WebSearchTool] Search failed for {query!r}: {exc}")
            return [ToolResult(
                tool=self.name, query=query,
                title="[Error] Web search failed",
                content="", url="", error=str(exc)
            )]
