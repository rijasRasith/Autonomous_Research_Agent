# Yeh file AgentState define karti hai — graph ke har node ko yahi shared data milta hai aur yahi update hota hai.

import operator
from typing import Annotated, Any, Optional
from typing_extensions import TypedDict


class ResearchPlan(TypedDict, total=False):
    goal: str
    search_strategy: str
    required_information: list[str]
    initial_queries: list[str]
    suggested_tools: list[str]
    complexity: str


class ReflectionOutput(TypedDict, total=False):
    is_sufficient: bool
    missing_information: list[str]
    additional_queries: list[str]
    confidence_score: float
    reasoning: str


class AgentState(TypedDict, total=False):
    query: str
    force_refresh: bool
    research_plan: ResearchPlan
    selected_tools: list[str]
    raw_results: Annotated[list[dict[str, Any]], operator.add]
    cleaned_corpus: str
    reflection: ReflectionOutput
    iteration_count: int
    max_iterations: int
    summary: dict[str, Any]
    export_paths: dict[str, str]
    memory_hit: bool
    cached_result: Optional[dict]
    error: Optional[str]
    warnings: Annotated[list[str], operator.add]

