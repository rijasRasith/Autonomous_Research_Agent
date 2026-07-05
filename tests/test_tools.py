import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from backend.tools.base_tool import ToolResult
from backend.tools.content_cleaner import clean_and_deduplicate


def make_result(content: str, tool: str = "web_search", url: str = "http://example.com", score: float = 0.8) -> ToolResult:
    return ToolResult(
        tool=tool,
        query="test query",
        title="Test Title",
        content=content,
        url=url,
        source_type="web",
        relevance_score=score,
    )


class TestContentCleaner:

    def test_clean_empty_results(self):
        corpus, cleaned = clean_and_deduplicate([])
        assert corpus == ""
        assert cleaned == []

    def test_removes_duplicates(self):
        long_text = "This is a sufficiently long paragraph that should pass the minimum length filter. " * 3
        r1 = make_result(long_text)
        r2 = make_result(long_text)
        corpus, cleaned = clean_and_deduplicate([r1, r2])
        assert len(cleaned) == 1

    def test_strips_html_tags(self):
        r = make_result("<nav>Navigation menu</nav><p>This is actual content that is long enough to matter.</p>" * 3)
        corpus, cleaned = clean_and_deduplicate([r])
        assert "<nav>" not in corpus
        assert "Navigation menu" not in corpus

    def test_filters_short_paragraphs(self):
        r = make_result("Short.\n\n" + "This is a much longer paragraph that definitely exceeds sixty characters. " * 4)
        corpus, cleaned = clean_and_deduplicate([r])
        assert "Short." not in corpus

    def test_sorts_by_relevance_score(self):
        low = make_result("Low relevance content that is definitely long enough to pass the filter. " * 2, score=0.2)
        high = make_result("High relevance content that is definitely long enough to pass the filter. " * 2, score=0.9)
        corpus, _ = clean_and_deduplicate([low, high])
        high_pos = corpus.find("High relevance")
        low_pos = corpus.find("Low relevance")
        assert high_pos < low_pos

    def test_result_with_error_is_skipped(self):
        bad = ToolResult(tool="web_search", query="q", title="t", content="", url="", error="Failed")
        good = make_result("Good content that is definitely long enough to pass all the filters." * 3)
        corpus, cleaned = clean_and_deduplicate([bad, good])
        assert len(cleaned) == 1

    def test_corpus_separator(self):
        r1 = make_result("First source content that is long enough to pass the minimum filter." * 3, url="http://a.com")
        r2 = make_result("Second source content different from first, long enough to pass." * 3, url="http://b.com")
        corpus, _ = clean_and_deduplicate([r1, r2])
        assert "---" in corpus


class TestWebSearchTool:

    @pytest.mark.asyncio
    async def test_returns_error_result_when_client_unavailable(self):
        with patch("backend.tools.web_search_tool.settings") as mock_settings:
            mock_settings.tavily_api_key = "invalid_key"
            from backend.tools.web_search_tool import WebSearchTool
            tool = WebSearchTool()
            tool._client = None
            results = await tool.run("test query")
            assert len(results) == 1
            assert results[0].error is not None

    @pytest.mark.asyncio
    async def test_tavily_response_parsing(self):
        from backend.tools.web_search_tool import WebSearchTool
        tool = WebSearchTool()
        tool._client = MagicMock()
        tool._client.search = MagicMock(return_value={
            "answer": "A synthesized answer",
            "results": [
                {"title": "Result 1", "url": "http://example.com", "content": "Some content here", "score": 0.9},
            ]
        })
        results = await tool.run("test")
        assert any(r.title == "Tavily Synthesized Answer" for r in results)
        assert any(r.title == "Result 1" for r in results)


class TestWikipediaTool:

    @pytest.mark.asyncio
    async def test_empty_response_returns_empty_list(self):
        import aiohttp
        from unittest.mock import patch, AsyncMock
        from backend.tools.wikipedia_tool import WikipediaTool

        tool = WikipediaTool()

        with patch.object(tool, "_search_titles", new=AsyncMock(return_value=[])):
            results = await tool.run("unknown query xyz")
            assert results == []

    @pytest.mark.asyncio
    async def test_result_has_correct_source_type(self):
        from backend.tools.wikipedia_tool import WikipediaTool
        tool = WikipediaTool()

        with patch.object(tool, "_search_titles", new=AsyncMock(return_value=["Python (programming language)"])):
            with patch.object(tool, "_fetch_summary", new=AsyncMock(return_value=ToolResult(
                tool="wikipedia",
                query="Python",
                title="Python (programming language)",
                content="Python is a high-level general-purpose programming language. " * 10,
                url="https://en.wikipedia.org/wiki/Python",
                source_type="wikipedia",
                relevance_score=0.85,
            ))):
                results = await tool.run("Python programming")
                assert results[0].source_type == "wikipedia"


class TestToolResult:

    def test_to_dict_serialization(self):
        r = ToolResult(
            tool="web_search",
            query="test",
            title="Test Title",
            content="Some content",
            url="http://example.com",
            source_type="web",
            relevance_score=0.7,
        )
        d = r.to_dict()
        assert d["tool"] == "web_search"
        assert d["title"] == "Test Title"
        assert d["relevance_score"] == 0.7
        assert d["error"] is None

    def test_error_result_to_dict(self):
        r = ToolResult(
            tool="github",
            query="test",
            title="Error",
            content="",
            url="",
            error="API rate limited",
        )
        d = r.to_dict()
        assert d["error"] == "API rate limited"
        assert d["content"] == ""
