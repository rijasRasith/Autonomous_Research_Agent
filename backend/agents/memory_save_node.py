from pathlib import Path

from backend.memory.memory_store import get_memory_store
from backend.models.state import AgentState
from backend.utils.logger import get_logger

logger = get_logger(__name__)


async def memory_save_node(state: AgentState) -> dict:
    if state.get("memory_hit", False):
        logger.info("[MemorySave] Cache hit result — skipping save (already in DB)")
        return {}

    query = state.get("query", "")
    summary = state.get("summary", {})
    tools_used = state.get("selected_tools", [])
    iterations = state.get("iteration_count", 1)
    raw_results = state.get("raw_results", [])
    export_paths = state.get("export_paths", {})

    if not summary:
        logger.warning("[MemorySave] Empty summary — skipping save")
        return {}

    # Normalize export_paths to filenames only (portable across working directories)
    normalized_paths = {k: Path(v).name for k, v in export_paths.items() if v}

    store = get_memory_store()
    store.save(
        query=query,
        summary=summary,
        tools_used=tools_used,
        iterations=iterations,
        sources_count=len(raw_results),
        export_paths=normalized_paths,
    )
    logger.info(f"[MemorySave] Research result persisted for query: {query!r}")
    return {}

