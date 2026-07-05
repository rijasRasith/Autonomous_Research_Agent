# Tool registry — maps tool name strings to tool class instances.
# The planner/tool-selector returns names; the search node looks them up here.

from functools import lru_cache

from backend.tools.base_tool import BaseTool
from backend.tools.documentation_tool import DocumentationTool
from backend.tools.github_tool import GitHubTool
from backend.tools.news_tool import NewsTool
from backend.tools.web_search_tool import WebSearchTool
from backend.tools.wikipedia_tool import WikipediaTool
from backend.utils.logger import get_logger

logger = get_logger(__name__)

# All available tools — keys must match what the LLM planner/tool-selector returns
_TOOL_MAP: dict[str, type[BaseTool]] = {
    "web_search":    WebSearchTool,
    "wikipedia":     WikipediaTool,
    "github":        GitHubTool,
    "documentation": DocumentationTool,
    "news":          NewsTool,
}


@lru_cache(maxsize=1)
def get_tool_registry() -> dict[str, BaseTool]:
    """
    Lazily instantiate every tool once and cache forever.
    Keeps Tavily clients, aiohttp sessions, etc. single-instance.
    """
    registry: dict[str, BaseTool] = {}
    for name, cls in _TOOL_MAP.items():
        try:
            registry[name] = cls()
            logger.info(f"[ToolRegistry] Registered: {name}")
        except Exception as exc:
            logger.error(f"[ToolRegistry] Failed to register {name}: {exc}")
    return registry


def get_tool(name: str) -> BaseTool | None:
    """Return a specific tool by name, or None if not registered."""
    return get_tool_registry().get(name)


def list_available_tools() -> list[str]:
    """Return all registered tool names."""
    return list(get_tool_registry().keys())
