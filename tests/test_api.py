import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def test_root_endpoint(client):
    response = client.get("/api/v1/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "version" in data


def test_health_endpoint(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "environment" in data


def test_history_endpoint_empty(client, mock_memory_store):
    response = client.get("/api/v1/research/history")
    assert response.status_code == 200
    assert response.json() == []


def test_history_endpoint_with_records(client, mock_memory_store):
    mock_memory_store.get_all.return_value = [
        {
            "id": 1,
            "query": "LangGraph overview",
            "tools_used": ["web_search"],
            "iterations": 1,
            "sources_count": 5,
            "export_paths": {},
            "created_at": "2025-01-01T00:00:00",
        }
    ]
    response = client.get("/api/v1/research/history")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["query"] == "LangGraph overview"


def test_download_nonexistent_file(client):
    response = client.get("/api/v1/research/download/does_not_exist.pdf")
    assert response.status_code == 404


def test_research_query_too_short(client):
    response = client.post("/api/v1/research", json={"query": "AI"})
    assert response.status_code == 422


def test_research_query_empty(client):
    response = client.post("/api/v1/research", json={"query": ""})
    assert response.status_code == 422


@pytest.mark.parametrize("topic", [
    "What is artificial intelligence?",
    "Python programming best practices",
    "How does LangGraph work?",
])
def test_research_valid_query_structure(topic, client):
    with patch("backend.api.routes.get_research_graph") as mock_graph:
        compiled = MagicMock()
        compiled.ainvoke = AsyncMock(return_value={
            "query": topic,
            "summary": {
                "executive_summary": "Test summary",
                "key_points": ["Point 1", "Point 2"],
                "important_findings": [],
                "references": [],
                "actionable_insights": ["Insight 1"],
            },
            "selected_tools": ["web_search"],
            "iteration_count": 1,
            "raw_results": [{"content": "test", "url": "http://example.com"}],
            "export_paths": {},
            "memory_hit": False,
            "error": None,
        })
        mock_graph.return_value = compiled

        response = client.post("/api/v1/research", json={"query": topic})
        assert response.status_code == 200
        data = response.json()
        assert data["query"] == topic
        assert data["status"] in ["completed", "cached", "completed_with_warnings"]
        assert "summary" in data
        assert "export_paths" in data
        assert "memory_hit" in data


def test_research_force_refresh_flag(client):
    with patch("backend.api.routes.get_research_graph") as mock_graph:
        compiled = MagicMock()
        compiled.ainvoke = AsyncMock(return_value={
            "summary": {"executive_summary": "test", "key_points": [], "important_findings": [], "references": [], "actionable_insights": []},
            "selected_tools": ["web_search"],
            "iteration_count": 1,
            "raw_results": [],
            "export_paths": {},
            "memory_hit": False,
            "error": None,
        })
        mock_graph.return_value = compiled

        response = client.post("/api/v1/research", json={"query": "Test query here", "force_refresh": True})
        assert response.status_code == 200


def test_research_returns_processing_time(client):
    with patch("backend.api.routes.get_research_graph") as mock_graph:
        compiled = MagicMock()
        compiled.ainvoke = AsyncMock(return_value={
            "summary": {"executive_summary": "test", "key_points": [], "important_findings": [], "references": [], "actionable_insights": []},
            "selected_tools": [],
            "iteration_count": 1,
            "raw_results": [],
            "export_paths": {},
            "memory_hit": False,
            "error": None,
        })
        mock_graph.return_value = compiled

        response = client.post("/api/v1/research", json={"query": "Technology trends"})
        assert response.status_code == 200
        assert response.json()["processing_time_seconds"] is not None
