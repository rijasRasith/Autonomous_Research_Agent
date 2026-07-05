# Search node — Phase 7+8+9+10:
# Runs selected tools in parallel (asyncio.gather), cleans results, builds corpus.

import asyncio

from backend.models.state import AgentState
from backend.tools.content_cleaner import clean_and_deduplicate
from backend.tools.tool_registry import get_tool, list_available_tools
from backend.utils.config import settings
from backend.utils.logger import get_logger

logger = get_logger(__name__)

# Max queries to run per tool per iteration (keeps costs + latency bounded)
_MAX_QUERIES_PER_TOOL = 2


async def _run_single_tool(tool_name: str, query: str) -> list[dict]:
    """Run one tool for one query with timeout protection. Returns list of result dicts."""
    tool = get_tool(tool_name)
    if tool is None:
        logger.warning(f"[SearchNode] Unknown tool requested: {tool_name!r}")
        return []

    try:
        results = await asyncio.wait_for(
            tool.run(query, max_results=settings.max_search_results),
            timeout=float(settings.max_tool_timeout_seconds),
        )
        return [r.to_dict() for r in results if r.content or r.error]
    except asyncio.TimeoutError:
        logger.warning(f"[SearchNode] Tool {tool_name!r} timed out for query: {query!r}")
        return []
    except Exception as exc:
        logger.error(f"[SearchNode] Tool {tool_name!r} crashed for {query!r}: {exc}")
        return []


async def search_node(state: AgentState) -> dict:
    query = state.get("query", "")
    plan = state.get("research_plan", {})
    selected_tools = state.get("selected_tools", ["web_search"])
    reflection = state.get("reflection", {})
    iteration = state.get("iteration_count", 0)

    # On first iteration use the planner's queries; on re-loops use the reflection's new queries
    queries: list[str] = (
        reflection.get("additional_queries")
        or plan.get("initial_queries")
        or [query]
    )
    queries = queries[:_MAX_QUERIES_PER_TOOL]  # cap

    # Only use tools that are actually registered
    available = list_available_tools()
    active_tools = [t for t in selected_tools if t in available]
    if not active_tools:
        logger.warning("[SearchNode] No valid tools selected — falling back to web_search")
        active_tools = ["web_search"]

    logger.info(
        f"[SearchNode] Iteration={iteration} | "
        f"tools={active_tools} | "
        f"queries={queries}"
    )

    # --- Phase 8: Parallel tool execution ---
    # Build every (tool, query) pair as a separate coroutine
    tasks = [
        _run_single_tool(tool_name, q)
        for tool_name in active_tools
        for q in queries
    ]

    logger.info(f"[SearchNode] Launching {len(tasks)} parallel tool calls...")
    raw_batches = await asyncio.gather(*tasks, return_exceptions=True)

    # Flatten results, skip any gather-level exceptions
    raw_dicts: list[dict] = []
    for batch in raw_batches:
        if isinstance(batch, list):
            raw_dicts.extend(batch)
        elif isinstance(batch, Exception):
            logger.error(f"[SearchNode] gather exception: {batch}")

    logger.info(f"[SearchNode] Total raw results: {len(raw_dicts)}")

    # --- Phase 9+10: Content extraction & cleaning ---
    # Reconstruct ToolResult-like objects from dicts for the cleaner
    from backend.tools.base_tool import ToolResult
    tool_results = [
        ToolResult(
            tool=d.get("tool", ""),
            query=d.get("query", query),
            title=d.get("title", ""),
            content=d.get("content", ""),
            url=d.get("url", ""),
            source_type=d.get("source_type", "web"),
            relevance_score=d.get("relevance_score", 0.5),
            error=d.get("error"),
        )
        for d in raw_dicts
    ]

    corpus, cleaned_results = clean_and_deduplicate(tool_results)

    if not corpus:
        logger.warning("[SearchNode] Empty corpus after cleaning — using raw content as fallback")
        # Fallback: join raw snippets without cleaning
        corpus = "\n\n---\n\n".join(
            d.get("content", "") for d in raw_dicts if d.get("content")
        )
        cleaned_results = raw_dicts

    logger.info(
        f"[SearchNode] Corpus ready | "
        f"sources={len(cleaned_results)} | "
        f"corpus_chars={len(corpus)}"
    )

    # Return raw_results as full dicts (they get appended via Annotated[list, operator.add])
    return {
        "raw_results": cleaned_results,
        "cleaned_corpus": corpus,
    }
