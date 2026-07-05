# Yeh file tool selector agent hai — LLM se poochha jaata hai ki is query ke liye kaunse tools use karne chahiye.

from backend.models.state import AgentState
from backend.prompts.summarizer_prompt import (
    TOOL_SELECTOR_SYSTEM_PROMPT,
    TOOL_SELECTOR_USER_PROMPT_TEMPLATE,
)
from backend.services.llm_service import get_llm_service
from backend.utils.logger import get_logger

logger = get_logger(__name__)

AVAILABLE_TOOLS = {"web_search", "wikipedia", "github", "documentation", "news"}


async def tool_selector_node(state: AgentState) -> dict:
    query = state.get("query", "")
    plan = state.get("research_plan", {})

    logger.info(f"[ToolSelectorAgent] Selecting tools for query: {query!r}")

    llm = get_llm_service()

    user_prompt = TOOL_SELECTOR_USER_PROMPT_TEMPLATE.format(
        goal=plan.get("goal", query),
        query=query,
        complexity=plan.get("complexity", "moderate"),
        suggested_tools=plan.get("suggested_tools", ["web_search"]),
    )

    try:
        result = await llm.ainvoke_json(
            system_prompt=TOOL_SELECTOR_SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )

        raw_tools = result.get("selected_tools", ["web_search"])
        selected = [t for t in raw_tools if t in AVAILABLE_TOOLS]

        if not selected:
            selected = ["web_search"]

        logger.info(
            f"[ToolSelectorAgent] Tools selected: {selected} | "
            f"reasoning: {result.get('reasoning', 'N/A')[:80]}"
        )
        return {"selected_tools": selected}

    except Exception as exc:
        logger.error(f"[ToolSelectorAgent] Failed, using fallback tools: {exc}")
        fallback = plan.get("suggested_tools", ["web_search"])
        fallback = [t for t in fallback if t in AVAILABLE_TOOLS] or ["web_search"]
        return {"selected_tools": fallback}
