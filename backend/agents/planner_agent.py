# Yeh file planner agent hai — user ki query lekar LLM se research plan banwata hai.

from backend.models.state import AgentState
from backend.prompts.planner_prompt import (
    PLANNER_SYSTEM_PROMPT,
    PLANNER_USER_PROMPT_TEMPLATE,
)
from backend.services.llm_service import get_llm_service
from backend.utils.config import settings
from backend.utils.logger import get_logger

logger = get_logger(__name__)


async def planner_node(state: AgentState) -> dict:
    query = state.get("query", "")
    logger.info(f"[PlannerAgent] Starting research planning for query: {query!r}")

    if not query.strip():
        logger.error("[PlannerAgent] Empty query received")
        return {"error": "Query cannot be empty"}

    llm = get_llm_service()
    user_prompt = PLANNER_USER_PROMPT_TEMPLATE.format(query=query)

    try:
        research_plan = await llm.ainvoke_json(
            system_prompt=PLANNER_SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )
        logger.info(
            f"[PlannerAgent] Plan created | "
            f"complexity={research_plan.get('complexity', 'unknown')} | "
            f"tools={research_plan.get('suggested_tools', [])} | "
            f"queries={len(research_plan.get('initial_queries', []))}"
        )
        return {
            "research_plan": research_plan,
            "iteration_count": 0,
            "max_iterations": settings.max_reflection_iterations,
        }

    except Exception as exc:
        logger.error(f"[PlannerAgent] Failed to generate research plan: {exc}")
        return {
            "error": f"Planner agent failed: {str(exc)}",
            "research_plan": {
                "goal": query,
                "search_strategy": "direct search",
                "required_information": [query],
                "initial_queries": [query],
                "suggested_tools": ["web_search"],
                "complexity": "simple",
            },
            "iteration_count": 0,
            "max_iterations": settings.max_reflection_iterations,
        }
