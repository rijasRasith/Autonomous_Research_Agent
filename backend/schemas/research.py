# Yeh file research API ke request aur response ka structure define karti hai — kya aayega, kya jaayega.

from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, Field


class ResearchRequest(BaseModel):
    query: str = Field(
        ...,
        min_length=3,
        max_length=500,
        description="The research topic or question",
        examples=["What are the best AI agent frameworks in 2025?"],
    )
    force_refresh: bool = Field(
        default=False,
        description="If true, skip memory cache and run fresh research",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "query": "Latest developments in LangGraph for building AI agents",
                "force_refresh": False,
            }
        }
    }


class ResearchSummary(BaseModel):
    executive_summary: str
    key_points: list[str] = Field(default_factory=list)
    important_findings: list[Any] = Field(default_factory=list)
    references: list[Any] = Field(default_factory=list)
    actionable_insights: list[str] = Field(default_factory=list)


class ResearchResponse(BaseModel):
    query: str
    status: str = Field(description="completed | completed_with_warnings | cached | failed")
    summary: Optional[ResearchSummary] = None
    tools_used: list[str] = Field(default_factory=list)
    iterations: int = Field(default=1)
    sources_count: int = Field(default=0)
    export_paths: dict[str, str] = Field(default_factory=dict)
    memory_hit: bool = Field(default=False, description="True if result was served from cache")
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    processing_time_seconds: Optional[float] = None


class HistoryItem(BaseModel):
    id: int
    query: str
    tools_used: list[str] = Field(default_factory=list)
    iterations: int = 1
    sources_count: int = 0
    export_paths: dict[str, str] = Field(default_factory=dict)
    created_at: str
