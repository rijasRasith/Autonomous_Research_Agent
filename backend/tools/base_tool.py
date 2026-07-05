# Base class for all research tools — every tool must implement run(query) -> list[dict]

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ToolResult:
    """Normalized result returned by every tool."""
    tool: str
    query: str
    title: str
    content: str
    url: str
    source_type: str = "web"          # web | github | wikipedia | docs | news
    relevance_score: float = 0.0
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "tool": self.tool,
            "query": self.query,
            "title": self.title,
            "content": self.content,
            "url": self.url,
            "source_type": self.source_type,
            "relevance_score": self.relevance_score,
            "error": self.error,
        }


class BaseTool(ABC):
    """Abstract base for all research tools."""

    name: str = "base"
    description: str = ""

    @abstractmethod
    async def run(self, query: str, max_results: int = 5) -> list[ToolResult]:
        """Execute the tool and return a list of normalized ToolResult objects."""
        ...
