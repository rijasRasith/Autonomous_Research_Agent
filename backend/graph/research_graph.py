# Yeh file pura LangGraph workflow banati hai — planner se lekar summarizer tak ka graph yahan define hota hai.

from functools import lru_cache

from langgraph.graph import END, START, StateGraph

from backend.agents.export_node import export_node
from backend.agents.memory_check_node import memory_check_node
from backend.agents.memory_save_node import memory_save_node
from backend.agents.planner_agent import planner_node
from backend.agents.reflection_agent import reflection_node
from backend.agents.search_node import search_node
from backend.agents.summarizer_agent import summarizer_node
from backend.agents.tool_selector_agent import tool_selector_node
from backend.models.state import AgentState
from backend.utils.logger import get_logger

logger = get_logger(__name__)


def route_after_memory_check(state: AgentState) -> str:
    if state.get("memory_hit", False):
        logger.info("[Graph] Cache hit — routing directly to END (skip full research)")
        return END
    logger.info("[Graph] No cache hit — routing to planner")
    return "planner"


def should_continue_research(state: AgentState) -> str:
    reflection = state.get("reflection", {})
    is_sufficient = reflection.get("is_sufficient", True)
    iteration = state.get("iteration_count", 0)
    max_iter = state.get("max_iterations", 3)

    if is_sufficient or iteration >= max_iter:
        logger.info(
            f"[Graph] Routing -> summarizer "
            f"(sufficient={is_sufficient}, iteration={iteration}/{max_iter})"
        )
        return "summarizer"
    logger.info(
        f"[Graph] Routing -> search (another iteration needed, "
        f"confidence={reflection.get('confidence_score', 0):.2f})"
    )
    return "search"


def build_research_graph() -> StateGraph:
    logger.info("Building research graph...")

    graph = StateGraph(AgentState)

    graph.add_node("memory_check", memory_check_node)
    graph.add_node("planner", planner_node)
    graph.add_node("tool_selector", tool_selector_node)
    graph.add_node("search", search_node)
    graph.add_node("reflection", reflection_node)
    graph.add_node("summarizer", summarizer_node)
    graph.add_node("export", export_node)
    graph.add_node("memory_save", memory_save_node)

    graph.add_edge(START, "memory_check")

    graph.add_conditional_edges(
        "memory_check",
        route_after_memory_check,
        {END: END, "planner": "planner"},
    )

    graph.add_edge("planner", "tool_selector")
    graph.add_edge("tool_selector", "search")
    graph.add_edge("search", "reflection")

    graph.add_conditional_edges(
        "reflection",
        should_continue_research,
        {"search": "search", "summarizer": "summarizer"},
    )

    graph.add_edge("summarizer", "export")
    graph.add_edge("export", "memory_save")
    graph.add_edge("memory_save", END)

    compiled = graph.compile()
    logger.info("Research graph compiled successfully")

    return compiled


@lru_cache(maxsize=1)
def get_research_graph():
    return build_research_graph()
