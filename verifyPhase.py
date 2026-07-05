"""
 7 Verification Suite
Tests every component: imports, registry, content cleaner, live tools, search node, graph, API.
Run with: venv\Scripts\python.exe verify.py
(no backslash escape issue — raw string below)
"""

import asyncio
import sys
import time
import io
import traceback

# Force UTF-8 output on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

PASS = "[PASS]"
FAIL = "[FAIL]"
INFO = "[INFO]"
WARN = "[WARN]"
SEP  = "-" * 62

results_summary: list[tuple[str, str]] = []


def header(title: str):
    print(f"\n{SEP}")
    print(f"  {title}")
    print(SEP)


def record(name: str, passed: bool, note: str = ""):
    tag = PASS if passed else FAIL
    msg = f"{tag} {name}"
    if note:
        msg += f" — {note}"
    print(msg)
    results_summary.append((name, "PASS" if passed else "FAIL"))


# ──────────────────────────────────────────────────────────────
# TEST 1 — Imports
# ──────────────────────────────────────────────────────────────
header("TEST 1 — Tool Package Imports")
try:
    from backend.tools.base_tool import BaseTool, ToolResult
    from backend.tools.web_search_tool import WebSearchTool
    from backend.tools.wikipedia_tool import WikipediaTool
    from backend.tools.github_tool import GitHubTool
    from backend.tools.documentation_tool import DocumentationTool
    from backend.tools.news_tool import NewsTool
    from backend.tools.content_cleaner import clean_and_deduplicate
    from backend.tools.tool_registry import get_tool_registry, list_available_tools, get_tool
    record("All tool imports", True)
except Exception as e:
    record("All tool imports", False, str(e))
    traceback.print_exc()
    sys.exit(1)


# ──────────────────────────────────────────────────────────────
# TEST 2 — Tool Registry
# ──────────────────────────────────────────────────────────────
header("TEST 2 — Tool Registry (5 tools expected)")
try:
    registry = get_tool_registry()
    available = list_available_tools()
    expected = {"web_search", "wikipedia", "github", "documentation", "news"}
    registered = set(available)
    missing = expected - registered
    record("All 5 tools registered", len(missing) == 0,
           f"missing={missing}" if missing else f"tools={sorted(registered)}")
    for name, tool in registry.items():
        has_run = hasattr(tool, "run") and callable(tool.run)
        record(f"  {name} has run()", has_run)
except Exception as e:
    record("Tool registry", False, str(e))
    traceback.print_exc()


# ──────────────────────────────────────────────────────────────
# TEST 3 — ToolResult Dataclass
# ──────────────────────────────────────────────────────────────
header("TEST 3 — ToolResult Dataclass")
try:
    tr = ToolResult(
        tool="test", query="hello", title="Test",
        content="Some meaningful content that is long enough to pass filters.",
        url="https://example.com", source_type="web", relevance_score=0.9,
    )
    d = tr.to_dict()
    assert d["tool"] == "test"
    assert d["relevance_score"] == 0.9
    assert "content" in d and "url" in d
    record("ToolResult creation + to_dict()", True)

    # Error result
    err = ToolResult(tool="test", query="q", title="E", content="", url="", error="timeout")
    assert err.error == "timeout"
    assert err.content == ""
    record("ToolResult with error field", True)
except Exception as e:
    record("ToolResult dataclass", False, str(e))
    traceback.print_exc()


# ──────────────────────────────────────────────────────────────
# TEST 4 — Content Cleaner
# ──────────────────────────────────────────────────────────────
header("TEST 4 — Content Cleaner")
try:
    PARAGRAPH_A = (
        "LangGraph is a stateful multi-agent framework that enables autonomous AI "
        "decision-making through a directed graph architecture where nodes represent "
        "individual computation steps and edges define the control flow."
    )
    PARAGRAPH_B = (
        "It uses directed graph structures where nodes perform computation and "
        "edges define the control flow between agents, enabling complex looping "
        "workflows that can adapt dynamically based on intermediate results."
    )

    samples = [
        ToolResult(
            tool="web_search", query="test", title="Doc A",
            content=f"<nav>Menu Items</nav>\n\n{PARAGRAPH_A}\n\nCookie policy: Accept cookies to continue.\n\n{PARAGRAPH_B}",
            url="https://a.com", source_type="web", relevance_score=0.9,
        ),
        # Exact duplicate of PARAGRAPH_A — should be deduped
        ToolResult(
            tool="wikipedia", query="test", title="Doc B (duplicate para)",
            content=f"{PARAGRAPH_A}\n\nWikipedia reference [1][2] additional text about multi-agent systems in AI.",
            url="https://wiki.org", source_type="wikipedia", relevance_score=0.85,
        ),
        # Too short — should be filtered
        ToolResult(
            tool="github", query="test", title="Doc C short",
            content="Short.",
            url="https://github.com", source_type="github", relevance_score=0.5,
        ),
        # Error result — should be skipped
        ToolResult(
            tool="web_search", query="test", title="Error Doc",
            content="", url="", error="Network error",
        ),
    ]

    corpus, cleaned = clean_and_deduplicate(samples)

    # Basic checks
    record("Corpus is non-empty", bool(corpus))
    record("Cleaned results non-empty", len(cleaned) >= 1)

    # HTML stripped
    record("HTML tags stripped", "<nav>" not in corpus and "<" not in corpus,
           f"HTML found: {'<nav>' in corpus}")

    # Cookie noise removed
    record("Cookie banner removed", "Cookie policy" not in corpus)

    # Wikipedia bracket references stripped
    record("Wikipedia [1][2] refs stripped", "[1]" not in corpus and "[2]" not in corpus)

    # Dedup: PARAGRAPH_A appears in both doc A and doc B — should only appear once
    count_para_a = corpus.count("LangGraph is a stateful multi-agent framework")
    record("Exact duplicate paragraph deduped", count_para_a == 1,
           f"found {count_para_a} copies")

    # Error results skipped (no empty content in cleaned)
    has_empty = any(not r.get("content") for r in cleaned)
    record("Error/empty results excluded", not has_empty)

    # Short content filtered
    all_long_enough = all(len(r.get("content", "")) >= 60 for r in cleaned)
    record("Short content (< 60 chars) filtered", all_long_enough)

    print(f"  {INFO} Corpus chars: {len(corpus)} | Sources: {len(cleaned)}")

except Exception as e:
    record("Content cleaner", False, str(e))
    traceback.print_exc()


# ──────────────────────────────────────────────────────────────
# TEST 5 — Web Search Tool (live Tavily call)
# ──────────────────────────────────────────────────────────────
header("TEST 5 — WebSearchTool (live Tavily)")
async def test_web_search():
    tool = WebSearchTool()
    t0 = time.perf_counter()
    results = await tool.run("LangGraph Python framework", max_results=3)
    elapsed = time.perf_counter() - t0
    has_content = [r for r in results if r.content and not r.error]
    record("WebSearchTool returns results", len(results) > 0, f"{len(results)} results in {elapsed:.1f}s")
    record("Results have content", len(has_content) > 0, f"{len(has_content)} with content")
    record("Results have URLs", all(r.url for r in has_content))
    record("Tool name is 'web_search'", all(r.tool == "web_search" for r in results))
    for r in has_content[:2]:
        print(f"  {INFO}  score={r.relevance_score:.2f} | {r.title[:65]}")
    return results

try:
    asyncio.run(test_web_search())
except Exception as e:
    record("WebSearchTool", False, str(e))
    traceback.print_exc()


# ──────────────────────────────────────────────────────────────
# TEST 6 — Wikipedia Tool (live, bool fix verified)
# ──────────────────────────────────────────────────────────────
header("TEST 6 — WikipediaTool (live, bool-fix applied)")
async def test_wikipedia():
    tool = WikipediaTool()
    t0 = time.perf_counter()
    results = await tool.run("artificial intelligence", max_results=2)
    elapsed = time.perf_counter() - t0
    has_content = [r for r in results if r.content and not r.error]
    record("WikipediaTool returns results", len(results) > 0, f"{len(results)} results in {elapsed:.1f}s")
    record("Wikipedia content extracted", len(has_content) > 0, f"{len(has_content)} with content")
    record("Wikipedia URLs are correct", all("wikipedia.org" in r.url for r in has_content))
    record("Source type is 'wikipedia'", all(r.source_type == "wikipedia" for r in has_content))
    for r in has_content:
        print(f"  {INFO}  {r.title[:55]} | chars={len(r.content)}")
    return results

try:
    asyncio.run(test_wikipedia())
except Exception as e:
    record("WikipediaTool", False, str(e))
    traceback.print_exc()


# ──────────────────────────────────────────────────────────────
# TEST 7 — GitHub Tool (live)
# ──────────────────────────────────────────────────────────────
header("TEST 7 — GitHubTool (live)")
async def test_github():
    tool = GitHubTool()
    t0 = time.perf_counter()
    results = await tool.run("LangGraph", max_results=2)
    elapsed = time.perf_counter() - t0
    has_content = [r for r in results if r.content and not r.error]
    record("GitHubTool returns results", len(results) > 0, f"{len(results)} results in {elapsed:.1f}s")
    record("GitHub content includes README", any("README" in r.content or "Repository" in r.content for r in has_content))
    record("Source type is 'github'", all(r.source_type == "github" for r in has_content))
    for r in has_content:
        print(f"  {INFO}  {r.title[:55]} | chars={len(r.content)}")
    return results

try:
    asyncio.run(test_github())
except Exception as e:
    record("GitHubTool", False, str(e))
    traceback.print_exc()


# ──────────────────────────────────────────────────────────────
# TEST 8 — Search Node: Parallel Execution 
# ──────────────────────────────────────────────────────────────
header("TEST 8 — Search Node — Parallel asyncio.gather")
async def test_search_node():
    from backend.agents.search_node import search_node
    state = {
        "query": "Python async programming",
        "selected_tools": ["web_search", "wikipedia"],
        "research_plan": {
            "initial_queries": ["Python asyncio tutorial", "async await Python"]
        },
        "raw_results": [],
        "warnings": [],
        "iteration_count": 0,
    }
    t0 = time.perf_counter()
    result = await search_node(state)
    elapsed = time.perf_counter() - t0

    corpus = result.get("cleaned_corpus", "")
    sources = result.get("raw_results", [])
    tools_used = {r.get("tool") for r in sources}

    record("search_node returns corpus", bool(corpus), f"{len(corpus)} chars in {elapsed:.1f}s")
    record("search_node returns sources", len(sources) > 0, f"{len(sources)} sources")
    record("web_search tool executed", "web_search" in tools_used)
    record("Result dict has correct keys",
           "cleaned_corpus" in result and "raw_results" in result)
    # Parallel: both queries fired simultaneously — total time should be < 2× single
    # Just check it completed in a reasonable time for 4 parallel calls
    record("Parallel execution fast enough", elapsed < 25.0, f"{elapsed:.1f}s (limit 25s)")

    print(f"  {INFO} Tools with results: {sorted(tools_used)}")
    print(f"  {INFO} Corpus preview: {corpus[:100].replace(chr(10), ' ')}...")

try:
    asyncio.run(test_search_node())
except Exception as e:
    record("search_node", False, str(e))
    traceback.print_exc()


# ──────────────────────────────────────────────────────────────
# TEST 9 — LangGraph Compilation
# ──────────────────────────────────────────────────────────────
header("TEST 9 — LangGraph Graph Compilation")
try:
    from backend.graph.research_graph import build_research_graph
    graph = build_research_graph()
    record("Graph compiles without error", graph is not None)
    record("Graph is CompiledStateGraph", "Compiled" in type(graph).__name__,
           type(graph).__name__)
except Exception as e:
    record("LangGraph compilation", False, str(e))
    traceback.print_exc()


# ──────────────────────────────────────────────────────────────
# TEST 10 — FastAPI App
# ──────────────────────────────────────────────────────────────
header("TEST 10 — FastAPI App & Routes")
try:
    from backend.main import app
    from backend.api.routes import router as api_router
    from backend.utils.config import settings
    from fastapi.routing import APIRoute

    # Routes are on the APIRouter object; app.include_router adds a prefix.
    # Reconstruct full paths: prefix + router route path.
    prefix = settings.api_prefix.rstrip("/")   # "/api/v1"
    router_paths = [
        prefix + r.path
        for r in api_router.routes
        if isinstance(r, APIRoute)
    ]

    record("FastAPI app loads", True, f"{len(router_paths)} APIRoutes registered")

    required_paths = ["/api/v1/", "/api/v1/health", "/api/v1/research"]
    for path in required_paths:
        found = path in router_paths
        record(f"Route '{path}' exists", found,
               "" if found else f"available={router_paths}")

    # Schema validation
    from backend.schemas.research import ResearchRequest
    req = ResearchRequest(query="test query")
    assert req.query == "test query"
    record("ResearchRequest schema works", True)

except Exception as e:
    record("FastAPI app", False, str(e))
    traceback.print_exc()


# ──────────────────────────────────────────────────────────────
# FINAL SUMMARY
# ──────────────────────────────────────────────────────────────
header("FINAL SUMMARY")
passed = [n for n, s in results_summary if s == "PASS"]
failed = [n for n, s in results_summary if s == "FAIL"]

print(f"  Passed : {len(passed)}")
print(f"  Failed : {len(failed)}")
if failed:
    print(f"\n  FAILED TESTS:")
    for f in failed:
        print(f"    {FAIL} {f}")
else:
    print(f"\n  All checks passed!")
print(f"\n{SEP}\n")
