import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture(scope="session")
def client():
    from backend.main import app
    with TestClient(app) as c:
        yield c


@pytest.fixture
def mock_llm_service():
    """
    Patch get_llm_service everywhere it is called from within agent modules.
    Using the source module path ensures the lru_cache singleton is bypassed.
    """
    targets = [
        "backend.agents.planner_agent.get_llm_service",
        "backend.agents.tool_selector_agent.get_llm_service",
        "backend.agents.reflection_agent.get_llm_service",
        "backend.agents.summarizer_agent.get_llm_service",
        "backend.agents.memory_check_node.get_llm_service",
    ]
    service = MagicMock()
    service.ainvoke_json = AsyncMock()
    service.ainvoke_text = AsyncMock()

    patchers = [patch(t, return_value=service) for t in targets]
    for p in patchers:
        p.start()
    yield service
    for p in patchers:
        p.stop()


@pytest.fixture
def mock_memory_store():
    """
    Patch get_memory_store in every module that imports it so the real SQLite
    DB is never touched during tests.
    """
    targets = [
        "backend.agents.memory_check_node.get_memory_store",
        "backend.agents.memory_save_node.get_memory_store",
        "backend.api.routes.get_memory_store",
    ]
    store = MagicMock()
    store.find.return_value = None
    store.save.return_value = None
    store.get_all.return_value = []

    patchers = [patch(t, return_value=store) for t in targets]
    for p in patchers:
        p.start()
    yield store
    for p in patchers:
        p.stop()


@pytest.fixture
def sample_research_plan():
    return {
        "goal": "Understand LangGraph",
        "search_strategy": "search technical documentation and GitHub",
        "required_information": ["what is LangGraph", "how to use it", "examples"],
        "initial_queries": ["LangGraph tutorial", "LangGraph examples"],
        "suggested_tools": ["web_search", "github"],
        "complexity": "moderate",
    }


@pytest.fixture
def sample_summary():
    return {
        "executive_summary": "LangGraph is a framework for building stateful multi-actor applications.",
        "key_points": ["Built on top of LangChain", "Uses graph-based workflows"],
        "important_findings": ["Supports cycles and conditional edges"],
        "references": [{"title": "LangGraph Docs", "url": "https://langchain-ai.github.io/langgraph/", "relevance": "Official"}],
        "actionable_insights": ["Use StateGraph for complex agent workflows"],
    }
