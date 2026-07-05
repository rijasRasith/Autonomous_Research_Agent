import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestPlannerAgent:

    @pytest.mark.asyncio
    async def test_returns_plan_with_required_fields(
        self, mock_llm_service, sample_research_plan
    ):
        mock_llm_service.ainvoke_json = AsyncMock(return_value=sample_research_plan)

        from backend.agents.planner_agent import planner_node

        result = await planner_node({"query": "What is LangGraph?"})

        assert "research_plan" in result
        assert "iteration_count" in result
        assert result["iteration_count"] == 0

    @pytest.mark.asyncio
    async def test_empty_query_returns_error(self, mock_llm_service):
        from backend.agents.planner_agent import planner_node

        result = await planner_node({"query": ""})
        assert "error" in result

    @pytest.mark.asyncio
    async def test_llm_failure_returns_fallback_plan(self, mock_llm_service):
        mock_llm_service.ainvoke_json = AsyncMock(
            side_effect=Exception("LLM unreachable")
        )
        from backend.agents.planner_agent import planner_node

        result = await planner_node({"query": "Machine learning overview"})
        assert "research_plan" in result
        assert result["research_plan"]["goal"] == "Machine learning overview"


class TestToolSelectorAgent:

    @pytest.mark.asyncio
    async def test_selects_valid_tools_only(self, mock_llm_service):
        mock_llm_service.ainvoke_json = AsyncMock(
            return_value={
                "selected_tools": ["web_search", "invalid_tool", "github"],
                "reasoning": "Use web and github for tech topics",
            }
        )
        from backend.agents.tool_selector_agent import tool_selector_node

        result = await tool_selector_node(
            {
                "query": "Python libraries",
                "research_plan": {
                    "goal": "Find Python libs",
                    "complexity": "moderate",
                    "suggested_tools": [],
                },
            }
        )
        assert "web_search" in result["selected_tools"]
        assert "github" in result["selected_tools"]
        assert "invalid_tool" not in result["selected_tools"]

    @pytest.mark.asyncio
    async def test_fallback_to_web_search_on_empty_selection(self, mock_llm_service):
        mock_llm_service.ainvoke_json = AsyncMock(
            return_value={"selected_tools": [], "reasoning": ""}
        )
        from backend.agents.tool_selector_agent import tool_selector_node

        result = await tool_selector_node(
            {
                "query": "Something",
                "research_plan": {
                    "goal": "Find stuff",
                    "complexity": "simple",
                    "suggested_tools": [],
                },
            }
        )
        assert result["selected_tools"] == ["web_search"]

    @pytest.mark.asyncio
    async def test_llm_failure_falls_back_gracefully(self, mock_llm_service):
        mock_llm_service.ainvoke_json = AsyncMock(side_effect=Exception("timeout"))
        from backend.agents.tool_selector_agent import tool_selector_node

        result = await tool_selector_node(
            {
                "query": "Science news",
                "research_plan": {
                    "goal": "Science",
                    "complexity": "simple",
                    "suggested_tools": ["news"],
                },
            }
        )
        assert len(result["selected_tools"]) > 0


class TestReflectionAgent:

    @pytest.mark.asyncio
    async def test_forces_completion_at_max_iterations(self, mock_llm_service):
        mock_llm_service.ainvoke_json = AsyncMock(
            return_value={
                "is_sufficient": False,
                "confidence_score": 0.2,
                "missing_information": ["more data needed"],
                "additional_queries": ["more queries"],
                "reasoning": "Not enough data",
            }
        )
        from backend.agents.reflection_agent import reflection_node

        result = await reflection_node(
            {
                "query": "test",
                "research_plan": {},
                "raw_results": [],
                "cleaned_corpus": "some data",
                "iteration_count": 2,
                "max_iterations": 3,
            }
        )
        assert result["reflection"]["is_sufficient"] is True

    @pytest.mark.asyncio
    async def test_returns_llm_decision_when_iterations_remain(self, mock_llm_service):
        mock_llm_service.ainvoke_json = AsyncMock(
            return_value={
                "is_sufficient": True,
                "confidence_score": 0.9,
                "missing_information": [],
                "additional_queries": [],
                "reasoning": "Enough information gathered",
            }
        )
        from backend.agents.reflection_agent import reflection_node

        result = await reflection_node(
            {
                "query": "AI agents",
                "research_plan": {
                    "goal": "Understand AI agents",
                    "required_information": [],
                },
                "raw_results": [{"content": "some content"}],
                "cleaned_corpus": "Good content here. " * 50,
                "iteration_count": 0,
                "max_iterations": 3,
            }
        )
        assert result["reflection"]["is_sufficient"] is True
        assert result["iteration_count"] == 1

    @pytest.mark.asyncio
    async def test_llm_failure_defaults_to_sufficient(self, mock_llm_service):
        mock_llm_service.ainvoke_json = AsyncMock(side_effect=Exception("LLM failed"))
        from backend.agents.reflection_agent import reflection_node

        result = await reflection_node(
            {
                "query": "test",
                "research_plan": {},
                "raw_results": [{"content": "x"}],
                "cleaned_corpus": "something",
                "iteration_count": 0,
                "max_iterations": 3,
            }
        )
        assert result["reflection"]["is_sufficient"] is True


class TestMemoryCheckNode:

    @pytest.mark.asyncio
    async def test_no_cache_hit_proceeds_to_planner(self, mock_memory_store):
        from backend.agents.memory_check_node import memory_check_node

        result = await memory_check_node({"query": "Brand new query here"})
        assert result["memory_hit"] is False

    @pytest.mark.asyncio
    async def test_cache_hit_reuse_populates_state(
        self, mock_llm_service, mock_memory_store
    ):
        cached_data = {
            "id": 1,
            "query": "LangGraph",
            "summary": {
                "executive_summary": "cached summary",
                "key_points": [],
                "important_findings": [],
                "references": [],
                "actionable_insights": [],
            },
            "tools_used": ["web_search"],
            "iterations": 2,
            "sources_count": 5,
            "export_paths": {"markdown": "report.md"},
            "created_at": "2025-01-01T00:00:00",
            "age_hours": 1.0,
        }
        mock_memory_store.find.return_value = cached_data
        mock_llm_service.ainvoke_json = AsyncMock(
            return_value={"decision": "reuse", "reasoning": "recent enough"}
        )

        from backend.agents.memory_check_node import memory_check_node

        result = await memory_check_node({"query": "LangGraph"})

        assert result["memory_hit"] is True
        assert result["summary"] == cached_data["summary"]


class TestMemorySaveNode:

    @pytest.mark.asyncio
    async def test_skips_save_on_cache_hit(self, mock_memory_store):
        from backend.agents.memory_save_node import memory_save_node

        result = await memory_save_node(
            {
                "query": "test",
                "summary": {"executive_summary": "cached"},
                "memory_hit": True,
            }
        )
        mock_memory_store.save.assert_not_called()
        assert result == {}

    @pytest.mark.asyncio
    async def test_saves_on_fresh_research(self, mock_memory_store):
        from backend.agents.memory_save_node import memory_save_node

        result = await memory_save_node(
            {
                "query": "Fresh research query",
                "summary": {"executive_summary": "fresh summary"},
                "selected_tools": ["web_search", "wikipedia"],
                "iteration_count": 2,
                "raw_results": [{"content": "c1"}, {"content": "c2"}],
                "export_paths": {"markdown": "report.md"},
                "memory_hit": False,
            }
        )
        mock_memory_store.save.assert_called_once()


class TestSummarizerAgent:

    @pytest.mark.asyncio
    async def test_returns_minimal_summary_on_empty_corpus(self, mock_llm_service):
        from backend.agents.summarizer_agent import summarizer_node

        result = await summarizer_node(
            {
                "query": "test",
                "research_plan": {},
                "cleaned_corpus": "",
                "raw_results": [],
            }
        )
        assert "summary" in result
        assert "No research data" in result["summary"]["executive_summary"]

    @pytest.mark.asyncio
    async def test_returns_llm_summary_on_valid_corpus(
        self, mock_llm_service, sample_summary
    ):
        mock_llm_service.ainvoke_json = AsyncMock(return_value=sample_summary)
        from backend.agents.summarizer_agent import summarizer_node

        result = await summarizer_node(
            {
                "query": "LangGraph",
                "research_plan": {"goal": "Understand LangGraph"},
                "cleaned_corpus": "A lot of collected content about LangGraph. " * 100,
                "raw_results": [{"url": "http://example.com", "content": "something"}],
            }
        )
        assert (
            result["summary"]["executive_summary"]
            == sample_summary["executive_summary"]
        )
        assert len(result["summary"]["key_points"]) > 0
