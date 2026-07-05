# Autonomous Research Agent

> **Built for Xiarch Bharat Pvt Ltd — Technical Assessment**  
> *A production-grade autonomous research system powered by Google Gemini, LangGraph, and FastAPI.*

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Architecture & Design Decisions](#2-architecture--design-decisions)
3. [Features I Built](#3-features-i-built)
4. [Tools the Agent Can Use](#4-tools-the-agent-can-use)
5. [Testing — Scenarios, Outputs & Bug Fixes](#5-testing--scenarios-outputs--bug-fixes)
6. [Installation](#6-installation)
7. [Running the Project](#7-running-the-project)
8. [Usage Guide & Example Inputs/Outputs](#8-usage-guide--example-inputsoutputs)
9. [Project Structure](#9-project-structure)
10. [Closing Notes](#10-closing-notes)

---

## 1. Project Overview

I built this project as a **true autonomous research agent** — one where the LLM is the decision-maker at every step of the workflow, not just a text generator at the end. The core idea I implemented is this: given a research question, the system should behave like a skilled analyst — deciding *what* to search, *which tools* to use, *whether the results are sufficient*, and *when to dig deeper*, all without any human in the loop.

The agent is built on top of **LangGraph**, a stateful graph execution engine that lets me define each stage of the research pipeline as a node, with conditional routing between them. **Google Gemini 2.5 Flash** serves as the reasoning engine throughout — planning, selecting tools, reflecting on results, and synthesizing the final report. The backend is a **FastAPI** REST API with persistent memory via **SQLite**, and exports in both **Markdown** and **PDF** formats.

The key design principle I followed was: **"Make one more enhancement — define each capability (web search, GitHub search, Wikipedia lookup, memory, export) as an independent tool and let the planner decide which tools to invoke."** That principle guided every architecture decision in this project.

---

## 2. Architecture & Design Decisions

I designed the system as a multi-node **LangGraph state machine**. Here is the full flow I implemented:

```
User Query (POST /api/v1/research)
          │
          ▼
  ┌── Memory Check Node ──────────────────────────┐
  │  Checks SQLite for a cached result.           │
  │  If found, asks LLM: "reuse or refresh?"      │
  │  If force_refresh=True → skip cache entirely  │
  └───────────────────────────────────────────────┘
          │ cache miss / refresh
          ▼
  ┌── Planner Agent ──────────────────────────────┐
  │  LLM reads the query and generates a          │
  │  structured ResearchPlan: complexity,         │
  │  sub-queries, and suggested tools.            │
  └───────────────────────────────────────────────┘
          │
          ▼
  ┌── Tool Selector Agent ────────────────────────┐
  │  LLM looks at the plan and the available      │
  │  tool registry, then picks the optimal set.   │
  └───────────────────────────────────────────────┘
          │
          ▼
  ┌── Search Node (asyncio.gather) ───────────────┐
  │  Runs ALL selected tools in PARALLEL.         │
  │  Each tool is called for each sub-query.      │
  │  Results cleaned & deduplicated.              │
  └───────────────────────────────────────────────┘
          │
          ▼
  ┌── Reflection Agent ───────────────────────────┐
  │  LLM evaluates: confidence score, gaps,       │
  │  new queries. Routes back to Search Node      │
  │  if more research is needed (max 3 loops).    │
  └───────────────────────────────────────────────┘
          │ sufficient
          ▼
  ┌── Summarizer Agent ───────────────────────────┐
  │  LLM synthesizes the entire corpus into       │
  │  a 5-section structured report.               │
  └───────────────────────────────────────────────┘
          │
          ▼
  ┌── Export Node ────────────────────────────────┐
  │  Saves Markdown + PDF to /reports/            │
  └───────────────────────────────────────────────┘
          │
          ▼
  ┌── Memory Save Node ───────────────────────────┐
  │  Persists result to SQLite for future reuse.  │
  └───────────────────────────────────────────────┘
          │
          ▼
  JSON Response → Client
```

**Why LangGraph?** I chose it because it gives me stateful, cyclical graph execution — something that isn't possible with a simple LangChain chain. The reflection → re-search loop is what makes this a true agent rather than a pipeline.

**Why Gemini 2.5 Flash?** It strikes the right balance between speed and reasoning quality. I also built in exponential backoff with `retryDelay` parsing for rate-limit (429) responses so the agent is resilient under load.

---

## 3. Features I Built

### 🧠 LLM-Driven Planning
The Planner Agent (`backend/agents/planner_agent.py`) is the first thing that runs on a fresh query. It uses the LLM to generate a `ResearchPlan` — a structured JSON containing the complexity rating, a list of targeted sub-queries, and a preliminary tool suggestion. The LLM does not just echo the user's question — it breaks it down intelligently.

### 🔧 Dynamic Tool Selection
The Tool Selector Agent (`backend/agents/tool_selector_agent.py`) reads both the plan and the live tool registry to decide which combination of tools will yield the best results. For a technical query about a framework, it might pick `web_search + github`. For a scientific topic, it might pick `wikipedia + web_search + news`. This decision is made by the LLM, not by hard-coded rules.

### ⚡ Parallel Tool Execution
The Search Node (`backend/agents/search_node.py`) uses `asyncio.gather()` to run all selected tools across all sub-queries simultaneously. A query that selects 2 tools and generates 2 sub-queries results in 4 network calls executed in parallel — significantly reducing latency.

### 🔁 Autonomous Reflection Loop
The Reflection Agent (`backend/agents/reflection_agent.py`) is what separates this from a simple search-and-summarize pipeline. After each search iteration, the LLM evaluates the collected corpus and assigns a confidence score. If it determines that key aspects of the query are still unanswered, it generates new, more targeted queries and routes back to the Search Node. This loop runs up to 3 times before forcing completion.

### 💾 Persistent Memory with Smart Cache
The Memory system (`backend/memory/memory_store.py`) uses SHA-256 query hashing for cache lookup. When a cached result is found, I don't blindly return it — I ask the LLM whether the cached data is still fresh enough to reuse, or whether a new search is warranted. The `force_refresh` flag bypasses all of this and always runs fresh research.

### 📄 Dual Export: Markdown + PDF
The Export Node generates both a structured Markdown report and a styled PDF report using ReportLab. The PDF includes branded colors, section headers, bulleted findings, and a footer. Both files are saved to the `reports/` directory with absolute paths.

### 🌐 REST API
The FastAPI backend (`backend/api/routes.py`) exposes three endpoints:
- `POST /api/v1/research` — submit a research query
- `GET /api/v1/research/history` — retrieve past queries from the database
- `GET /api/v1/research/download/{filename}` — download a generated Markdown or PDF report

---

## 4. Tools the Agent Can Use

I implemented each capability as an independent, modular tool extending a `BaseTool` interface. The LLM selects which tools to use per query.

| Tool | File | Description |
|------|------|-------------|
| **Web Search** | `tools/web_search_tool.py` | Calls the Tavily Search API. Returns the top 5–6 ranked results with relevance scores. |
| **GitHub Search** | `tools/github_tool.py` | Searches GitHub repositories by keyword (with stop-word filtering), fetches README content and star counts. |
| **Wikipedia** | `tools/wikipedia_tool.py` | Queries the Wikipedia API, retrieves summaries and introductory sections. |
| **News** | `tools/news_tool.py` | Uses Tavily's news-specific search to fetch recent articles on the topic. |
| **Documentation** | `tools/documentation_tool.py` | Scrapes and extracts clean content from official documentation URLs discovered during research. |

All tool results pass through a **Content Cleaner** (`tools/content_cleaner.py`) that:
- Strips HTML tags, navigation elements, cookie banners, and JavaScript blocks
- Deduplicates paragraphs using MD5 content hashing
- Filters out paragraphs shorter than 60 characters
- Sorts by relevance score before building the final corpus

---

## 5. Testing — Scenarios, Outputs & Bug Fixes

I tested the project from the user's perspective across 10 distinct scenarios. I did not just check that the server ran — I verified actual outputs against expected results, found real bugs, fixed them, and re-validated.

### Test Results Summary

| Test | Scenario | Expected | Actual | Status |
|------|----------|----------|--------|--------|
| T1 | Automated unit tests (`pytest`) | 40/40 pass | 40/40 pass | ✅ PASS |
| T2 | Server boot + `GET /health` | `{"status": "healthy"}` | Exact match | ✅ PASS |
| T3 | Full E2E research — tech query | `completed`, MD+PDF exported | `completed`, 36 sources, 3 iterations, both files | ✅ PASS |
| T4 | `force_refresh: true` flag | Cache bypassed, fresh run | Was broken → fixed → now works | ✅ PASS |
| T5 | `GET /research/history` | Return past queries | 8 records with full metadata | ✅ PASS |
| T6 | `GET /download/{filename}` | 200 + file bytes | Was 404 → fixed → 200 OK | ✅ PASS |
| T7 | Empty query `{"query": ""}` | `422 Unprocessable Entity` | `422` with validation message | ✅ PASS |
| T8 | Short query `{"query": "ab"}` | `422` min_length error | `422` with "at least 3 characters" | ✅ PASS |
| T9 | Download non-existent file | `404 Not Found` | `404 "Report not found: …"` | ✅ PASS |
| T10 | Repeat query (cache hit) | Fast response, `memory_hit: true` | 3.2s vs 75s fresh, `cached` status | ✅ PASS |

### Real Outputs I Observed

**T3 — "Best Python libraries for data science 2025"**
```json
{
  "status": "completed",
  "memory_hit": false,
  "iterations": 3,
  "sources_count": 36,
  "tools_used": ["web_search", "github"],
  "processing_time_seconds": 75.05,
  "export_paths": {
    "markdown": "D:\\...\\reports\\report_Best_Python_libraries_...md",
    "pdf":      "D:\\...\\reports\\report_Best_Python_libraries_...pdf"
  }
}
```

**T10 — Same query (cache hit)**
```json
{
  "status": "cached",
  "memory_hit": true,
  "processing_time_seconds": 3.2
}
```

The cache saved ~72 seconds of LLM+network time on repeat queries.

### Bugs I Found and Fixed

Testing revealed 9 real bugs that I identified, root-caused, and fixed:

| # | Bug | Root Cause | Fix |
|---|-----|-----------|-----|
| 1 | Reports saved to wrong folder | `reports_dir = "reports"` is relative to CWD at runtime | Changed to `@property` returning `PROJECT_ROOT / "reports"` — always absolute |
| 2 | Database in wrong location | Same issue with `sqlite:///./research_memory.db` | Made `database_url` an absolute-path property tied to project root |
| 3 | SQLAlchemy engine built before settings resolved | Module-level `create_engine(settings.database_url)` called too early | Wrapped in `@lru_cache` factory function, called lazily at first use |
| 4 | `updated_at` NULL on first insert | Column had `onupdate` but no `default` | Added `default=lambda: datetime.now(timezone.utc)` |
| 5 | `force_refresh=True` didn't bypass cache | The flag set `memory_hit=False` in state, but `memory_check_node` still ran a DB lookup and LLM decision that overrode it | Added `force_refresh` to `AgentState`; node short-circuits immediately if `True` |
| 6 | Download 404 for real files after server restart | `export_paths` stored as relative paths like `reports\\file.md` in DB | `memory_save_node` now normalises to filename only (`Path(v).name`) before persisting |
| 7 | GitHub tool always returned 0 results | Full natural-language queries like *"What are the best Python libraries for data visualization in 2025, specifically including Plotly?"* return 0 hits on GitHub's API | Added `_extract_keywords()` that strips stop words, question prefixes, and caps output at 6 keywords |
| 8 | PDF export crashed with `AttributeError: 'dict' object has no attribute 'split'` | LLM sometimes returns `key_points` / `findings` as dicts (`{"point": "…", "detail": "…"}`) rather than plain strings. ReportLab's `Paragraph` calls `.split()` internally | Added `_to_str(item: Any) -> str` helper that safely coerces any type to a plain, XML-escaped string |
| 9 | Markdown findings rendered as raw Python dict repr | Same LLM dict-output issue, but in `markdown_exporter.py` | Added `_item_to_md()` helper that renders `{title, description, significance}` dicts as proper bold-title + body Markdown |

Every bug was reproduced, fixed, and re-tested to confirm resolution before moving on.

---

## 6. Installation

### Prerequisites

- Python 3.11 or 3.13
- A **Google AI Studio** API key (for Gemini) — [get one free here](https://aistudio.google.com/app/apikey)
- A **Tavily** API key (for web/news search) — [get one free here](https://tavily.com)

### Step-by-Step Setup

**1. Clone the repository**
```bash
git clone <repository-url>
cd autonomous-research-agent
```

**2. Create and activate a virtual environment**
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python -m venv venv
source venv/bin/activate
```

**3. Install all dependencies**
```bash
pip install -r requirements.txt
```

Key dependencies installed:
- `fastapi` + `uvicorn` — REST API server
- `langgraph` — stateful agent graph execution
- `langchain-google-genai` — Gemini LLM integration
- `tavily-python` — web and news search
- `sqlalchemy` — SQLite persistence layer
- `reportlab` — PDF generation
- `aiohttp` — async HTTP for GitHub/Wikipedia tools
- `pydantic-settings` — environment variable management
- `pytest` + `pytest-asyncio` — test suite

**4. Configure environment variables**

Create a `.env` file in the project root (or edit the existing one):
```env
GOOGLE_API_KEY=your_gemini_api_key_here
TAVILY_API_KEY=your_tavily_api_key_here
APP_ENV=development
LOG_LEVEL=INFO
```

**5. Verify the installation**
```bash
python -m pytest tests/ -v
```
You should see `40 passed` with no errors.

---

## 7. Running the Project

**Start the API server** (always run from the project root directory):
```bash
venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

The server will print:
```
Autonomous Research Agent  v1.0.0
Environment : development
API Prefix  : /api/v1
Docs        : http://127.0.0.1:8000/docs
```

> ⚠️ **Important**: Always start the server from `d:\autonomous-research-agent\` (the project root). The system uses `Path(__file__).resolve()` to anchor all paths, so they are absolute regardless of your shell's current directory. The interactive Swagger UI is available at **http://127.0.0.1:8000/docs**.

---

## 8. Usage Guide & Example Inputs/Outputs

### Submit a Research Query

```bash
curl -X POST http://127.0.0.1:8000/api/v1/research \
  -H "Content-Type: application/json" \
  -d '{"query": "What is LangGraph and how is it used for building AI agents?", "force_refresh": false}'
```

**Example Response:**
```json
{
  "query": "What is LangGraph and how is it used for building AI agents?",
  "status": "completed",
  "memory_hit": false,
  "iterations": 2,
  "sources_count": 24,
  "tools_used": ["web_search", "github", "wikipedia"],
  "processing_time_seconds": 48.3,
  "summary": {
    "executive_summary": "LangGraph is a Python library built on top of LangChain that enables the construction of stateful, multi-actor applications...",
    "key_points": [
      "LangGraph models agent workflows as directed graphs with nodes and edges",
      "Supports cyclical execution enabling iterative refinement loops",
      "Integrates natively with all LangChain tools and LLM providers",
      "State is persisted across graph steps using TypedDict"
    ],
    "important_findings": [...],
    "actionable_insights": [...],
    "references": [...]
  },
  "export_paths": {
    "markdown": "D:\\autonomous-research-agent\\reports\\report_What_is_LangGraph_20260705_120000.md",
    "pdf":      "D:\\autonomous-research-agent\\reports\\report_What_is_LangGraph_20260705_120000.pdf"
  },
  "error": null
}
```

### Force Fresh Research (Bypass Cache)
```bash
curl -X POST http://127.0.0.1:8000/api/v1/research \
  -H "Content-Type: application/json" \
  -d '{"query": "Latest AI agent frameworks 2025", "force_refresh": true}'
```

### View Research History
```bash
curl http://127.0.0.1:8000/api/v1/research/history
```
Returns the last 20 queries with metadata (tools used, iteration count, source count, export paths).

### Download a Generated Report
```bash
# Download Markdown
curl http://127.0.0.1:8000/api/v1/research/download/report_What_is_LangGraph_20260705_120000.md -o output.md

# Download PDF
curl http://127.0.0.1:8000/api/v1/research/download/report_What_is_LangGraph_20260705_120000.pdf -o output.pdf
```

### Using the Swagger UI
Navigate to **http://127.0.0.1:8000/docs** in your browser. All three endpoints are documented there with example request bodies that you can execute directly from the browser.

### Input Validation
The API enforces these constraints automatically:

| Constraint | Rule | Response |
|-----------|------|----------|
| `query` too short | Must be at least 3 characters | `422 Unprocessable Entity` |
| `query` too long | Must be at most 500 characters | `422 Unprocessable Entity` |
| `query` empty | Empty string rejected | `422 Unprocessable Entity` |
| File not found | Non-existent filename in download | `404 Not Found` |

---

## 9. Project Structure

```
autonomous-research-agent/
│
├── backend/
│   ├── main.py                        # FastAPI app + lifespan + middleware
│   ├── api/
│   │   └── routes.py                  # REST endpoints (/research, /history, /download)
│   ├── agents/
│   │   ├── planner_agent.py           # LLM generates research plan + sub-queries
│   │   ├── tool_selector_agent.py     # LLM picks which tools to use
│   │   ├── search_node.py             # Parallel tool execution (asyncio.gather)
│   │   ├── reflection_agent.py        # LLM evaluates corpus; loops or continues
│   │   ├── summarizer_agent.py        # LLM synthesizes final structured report
│   │   ├── memory_check_node.py       # Cache lookup + LLM reuse-or-refresh decision
│   │   ├── memory_save_node.py        # Persists result to SQLite
│   │   └── export_node.py             # Triggers Markdown + PDF export
│   ├── graph/
│   │   └── research_graph.py          # LangGraph StateGraph: nodes + edges + routing
│   ├── tools/
│   │   ├── base_tool.py               # BaseTool + ToolResult dataclasses
│   │   ├── tool_registry.py           # Runtime tool registration + lookup
│   │   ├── web_search_tool.py         # Tavily web search
│   │   ├── github_tool.py             # GitHub repo search + README fetch
│   │   ├── wikipedia_tool.py          # Wikipedia API integration
│   │   ├── news_tool.py               # Tavily news search
│   │   ├── documentation_tool.py      # Documentation site scraper
│   │   └── content_cleaner.py         # HTML stripping, dedup, relevance sorting
│   ├── exporters/
│   │   ├── markdown_exporter.py       # Generates .md reports
│   │   └── pdf_exporter.py            # Generates branded .pdf reports (ReportLab)
│   ├── memory/
│   │   └── memory_store.py            # SHA-256 query hashing, SQLite CRUD
│   ├── database/
│   │   ├── models.py                  # SQLAlchemy ORM model (ResearchMemory)
│   │   └── session.py                 # Lazy engine init, SessionLocal factory
│   ├── models/
│   │   └── state.py                   # AgentState TypedDict (LangGraph state)
│   ├── schemas/
│   │   └── research.py                # Pydantic request/response models
│   ├── services/
│   │   └── llm_service.py             # Gemini client, JSON parsing, retry/backoff
│   ├── prompts/                        # All LLM system prompts (one per agent)
│   └── utils/
│       ├── config.py                   # Pydantic-settings, absolute path properties
│       └── logger.py                   # Structured logging setup
│
├── tests/
│   ├── conftest.py                     # Fixtures: mock LLM, test DB, FastAPI client
│   ├── test_agents.py                  # 15 unit tests for all agent nodes
│   ├── test_api.py                     # 12 integration tests for all REST endpoints
│   └── test_tools.py                   # 13 unit tests for tools + content cleaner
│
├── reports/                            # Generated research reports (MD + PDF)
├── research_memory.db                  # SQLite database (auto-created)
├── requirements.txt                    # All pinned Python dependencies
├── pytest.ini                          # pytest configuration
└── .env                                # API keys (not committed to git)
```

---

## 10. Closing Notes

I want to be direct with the interview panel: I did not just write code and submit it. I ran this system as a real user would, submitted actual queries, observed what broke, traced the root causes, fixed the bugs, and re-ran every test until every feature worked end-to-end.

The nine bugs I found during testing were all real issues — not theoretical edge cases. They ranged from path resolution bugs that silently saved files to the wrong directory, to LLM output schema variations that crashed the PDF renderer, to a `force_refresh` flag that appeared to work but was being silently overridden by the cache logic downstream. Finding and fixing these required understanding the full system — from FastAPI middleware, through LangGraph state flow, down to SQLite session management and ReportLab internals.

What I believe this project demonstrates:

- **System design** — I decomposed a complex problem (autonomous research) into a clean pipeline of independent, testable components connected by a state machine.
- **LLM integration** — I went beyond single-shot prompting to build a multi-step agentic loop where the model plans, acts, evaluates its own work, and decides whether to continue.
- **Resilience engineering** — I handled rate limits, partial failures, schema variations, and path resolution issues — the kind of real-world issues that tutorials never show you.
- **Test discipline** — 40 automated tests cover agents, API endpoints, and tools; 10 manual scenarios verified real end-to-end behaviour.
- **Code quality** — Every module has a single responsibility, every function is documented, and configuration is centralised with no hardcoded paths or secrets.

I built this system from scratch during this assessment period. I'm happy to walk through any part of the codebase, explain design decisions, or extend the system live during the technical discussion.

---

*Rijasrasith — Autonomous Research Agent Assessment, Xiarch Bharat Pvt Ltd*

---

## Developer Contact & Resources

*   **Portfolio**: [rasithnovfal.com](https://www.rasithnovfal.com/).
*   **GitHub Repository**: [Autonomous Research Agent Repo](https://github.com/rijasRasith/Autonomous_Research_Agent_Assessment_Xiarch_Bharat_Pvt_Ltd.git)
*   **GitHub Profile**: [rijasRasith](https://github.com/rijasRasith/)
*   **LinkedIn**: [Rasith Novfal](https://in.linkedin.com/in/rasithnovfal)
*   **Email**: [rijasrasithnovfal@gmail.com](mailto:rijasrasithnovfal@gmail.com)
