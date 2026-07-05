from backend.memory.memory_store import get_memory_store
from backend.models.state import AgentState
from backend.prompts.memory_prompt import (
    MEMORY_DECISION_SYSTEM_PROMPT,
    MEMORY_DECISION_USER_PROMPT_TEMPLATE,
)
from backend.services.llm_service import get_llm_service
from backend.utils.logger import get_logger

logger = get_logger(__name__)


async def memory_check_node(state: AgentState) -> dict:
    query = state.get("query", "")
    logger.info(f"[MemoryCheck] Checking cache for query: {query!r}")

    # If force_refresh was requested, skip cache entirely
    if state.get("force_refresh", False):
        logger.info("[MemoryCheck] force_refresh=True — bypassing cache, routing to planner")
        return {"memory_hit": False}

    store = get_memory_store()
    cached = store.find(query)

    if not cached:
        logger.info("[MemoryCheck] No cache entry found — proceeding to planner")
        return {"memory_hit": False}

    age_hours = cached["age_hours"]
    logger.info(f"[MemoryCheck] Cache found — age={age_hours:.1f}h — asking LLM to decide")

    llm = get_llm_service()
    user_prompt = MEMORY_DECISION_USER_PROMPT_TEMPLATE.format(
        query=query,
        age_hours=age_hours,
        cached_at=cached["created_at"],
    )

    try:
        result = await llm.ainvoke_json(
            system_prompt=MEMORY_DECISION_SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )
        decision = result.get("decision", "refresh")
        reasoning = result.get("reasoning", "")
        logger.info(f"[MemoryCheck] LLM decision: {decision!r} | {reasoning[:80]}")
    except Exception as exc:
        logger.error(f"[MemoryCheck] LLM decision failed ({exc}) — defaulting to refresh")
        decision = "refresh"

    if decision == "reuse":
        logger.info("[MemoryCheck] Reusing cached result — skipping full research")
        return {
            "memory_hit": True,
            "summary": cached["summary"],
            "selected_tools": cached["tools_used"],
            "iteration_count": cached["iterations"],
            "export_paths": cached["export_paths"],
        }

    logger.info("[MemoryCheck] LLM chose refresh — proceeding to planner")
    return {"memory_hit": False}
