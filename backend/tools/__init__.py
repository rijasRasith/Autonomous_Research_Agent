"""tools package — Web, GitHub, Wikipedia, Documentation, News tools (Phase 7)."""

from backend.tools.base_tool import BaseTool, ToolResult
from backend.tools.content_cleaner import clean_and_deduplicate
from backend.tools.documentation_tool import DocumentationTool
from backend.tools.github_tool import GitHubTool
from backend.tools.news_tool import NewsTool
from backend.tools.tool_registry import get_tool, get_tool_registry, list_available_tools
from backend.tools.web_search_tool import WebSearchTool
from backend.tools.wikipedia_tool import WikipediaTool

__all__ = [
    "BaseTool",
    "ToolResult",
    "WebSearchTool",
    "WikipediaTool",
    "GitHubTool",
    "DocumentationTool",
    "NewsTool",
    "clean_and_deduplicate",
    "get_tool",
    "get_tool_registry",
    "list_available_tools",
]
