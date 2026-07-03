# Phase 2 – Backend Foundation Implementation Guide

> **Project:** Autonomous Research Agent
> **Phase:** 2 — FastAPI Backend Foundation
> **Status:** ✅ Complete
> **Stack:** FastAPI · Pydantic Settings · Python Logging · Uvicorn

---

## Table of Contents

1. [Overview](#1-overview)
2. [Folder Exploration Guide](#2-folder-exploration-guide)
3. [How to Run](#3-how-to-run)
4. [Viewing Outputs](#4-viewing-outputs)
5. [Concepts Behind the Implementation](#5-concepts-behind-the-implementation)
6. [Learning Notes](#6-learning-notes)
7. [Next Steps — Phase 3 Preview](#7-next-steps--phase-3-preview)

---

## 1. Overview

### What is Phase 2?

Phase 2 establishes the **entire backend foundation** for the Autonomous Research Agent. Think of it as building the skeleton of a house before any rooms are furnished.

Before Phase 2, the project had:
- Empty folders
- An empty `main.py`
- No way to run anything

After Phase 2, the project has:
- A running **FastAPI web server**
- A **centralized configuration system** (reads API keys and settings from `.env`)
- A **structured logging system** (replaces `print()` statements)
- A **versioned API** (`/api/v1/...`) with live Swagger documentation
- Clean **separation of concerns** — every responsibility lives in its own module

### Why Does This Matter?

In a real-world AI project, the foundation determines how easy it is to extend, debug, and maintain the code. An interviewer will notice:

- Are configuration and secrets managed safely? ✅
- Is logging consistent and structured? ✅
- Are API routes separated from business logic? ✅
- Is the codebase modular and easy to navigate? ✅

Phase 2 answers "yes" to all of these.

### Goals Achieved

| Goal | Status |
|---|---|
| FastAPI app running with `uvicorn` | ✅ |
| Clean project architecture | ✅ |
| Environment variable management | ✅ |
| Centralized configuration (Pydantic Settings) | ✅ |
| Structured logging system | ✅ |
| API versioning (`/api/v1/`) | ✅ |
| `GET /` root endpoint | ✅ |
| `GET /health` health check endpoint | ✅ |
| Interactive Swagger documentation | ✅ |
| Foundation ready for LangGraph integration | ✅ |

---

## 2. Folder Exploration Guide

### Top-Level Structure

```
autonomous-research-agent/
│
├── backend/                  ← All server-side code lives here
│   ├── api/                  ← HTTP route handlers (controllers)
│   ├── agents/               ← LLM agents (Phase 3+)
│   ├── database/             ← SQLite models and sessions (Phase 13+)
│   ├── exporters/            ← PDF/Markdown export logic (Phase 14+)
│   ├── graph/                ← LangGraph workflow definition (Phase 3+)
│   ├── memory/               ← Memory/cache store (Phase 13+)
│   ├── models/               ← Pydantic domain models (Phase 3+)
│   ├── prompts/              ← LLM prompt templates (Phase 3+)
│   ├── schemas/              ← Request/response schemas (Phase 2 ✅)
│   ├── services/             ← Business services (Phase 3+)
│   ├── tools/                ← Research tools (Phase 7+)
│   ├── utils/                ← Config + Logger (Phase 2 ✅)
│   └── main.py               ← FastAPI app entry point (Phase 2 ✅)
│
├── frontend/                 ← React UI (Phase 16+)
├── reports/                  ← Generated PDF/Markdown reports
├── tests/                    ← Test suite (Phase 17+)
│
├── .env                      ← Secret API keys (never committed to Git)
├── .gitignore                ← Files Git should ignore
├── requirements.txt          ← Python dependencies
└── README.md                 ← Project overview
```

### Phase 2 Files — What to Read

The following files were **written in Phase 2** and are the ones to focus on now:

```
backend/
├── utils/
│   ├── config.py        ← #1 Read this first — all settings live here
│   └── logger.py        ← #2 Read next — how logging is configured
│
├── schemas/
│   └── responses.py     ← #3 Response shapes used by the API
│
├── api/
│   └── routes.py        ← #4 The actual API endpoints
│
└── main.py              ← #5 Read last — wires everything together
```

### File-by-File Purpose

#### `backend/utils/config.py`
The **single source of truth** for all application settings.

- Reads values from `.env` automatically using **Pydantic Settings**
- Validates types (e.g., `log_level` must be one of `DEBUG`, `INFO`, etc.)
- Returns a **cached singleton** — the `.env` file is read exactly once, no matter how many modules import it
- All other modules import `settings` from here instead of reading `.env` themselves

#### `backend/utils/logger.py`
Configures Python's built-in `logging` module once for the whole application.

- Any module calls `get_logger(__name__)` to get a named logger
- All logs share the same format: `2026-07-03 10:30:00 | INFO | module.name | message`
- Noisy third-party libraries (httpx, urllib3) are silenced to `WARNING` level

#### `backend/schemas/responses.py`
Defines the **shape** of what the API returns.

- `RootResponse` — shape of `GET /` response
- `HealthResponse` — shape of `GET /health` response
- `ErrorResponse` — standard error envelope for 4xx/5xx errors
- FastAPI uses these to auto-generate Swagger documentation

#### `backend/api/routes.py`
The **thin controller** layer — handles HTTP requests and delegates work.

- `GET /` — confirms the service is reachable
- `GET /health` — used by monitoring tools to check if the server is alive
- Contains stub comments for `POST /research`, `GET /history`, `GET /download` (coming in later phases)

#### `backend/main.py`
The **application entry point** — assembles all the pieces.

- Creates the FastAPI instance with metadata (title, version, description)
- Registers the CORS middleware (allows frontend to call the backend)
- Registers the request logging middleware (logs every request + response time)
- Mounts the router at `/api/v1`
- Uses a `lifespan` context manager for startup/shutdown events

---

## 3. How to Run

### Prerequisites

Before running, make sure you have:

- Python 3.12 installed
- The virtual environment activated
- A `.env` file with your API keys

### Step 1 — Activate the Virtual Environment

```bash
# Windows
venv\Scripts\activate

# Mac / Linux
source venv/bin/activate
```

You should see `(venv)` in your terminal prompt after activation.

### Step 2 — Verify Dependencies

```bash
pip install -r requirements.txt
```

Key packages used in Phase 2:

| Package | Version | Purpose |
|---|---|---|
| `fastapi` | ≥0.115 | Web framework |
| `uvicorn` | ≥0.30 | ASGI server |
| `pydantic-settings` | ≥2.0 | Settings management |
| `python-dotenv` | ≥1.0 | `.env` file loading |

### Step 3 — Check Your `.env` File

Make sure `.env` contains at minimum:

```env
GOOGLE_API_KEY=your_gemini_api_key_here
TAVILY_API_KEY=your_tavily_api_key_here
APP_NAME=Autonomous Research Agent
APP_ENV=development
LOG_LEVEL=INFO
```

> **Warning:** Never commit `.env` to Git. It is listed in `.gitignore` for this reason.

### Step 4 — Start the Server

From the **project root** (not inside `backend/`):

```bash
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

**What each flag means:**
- `backend.main:app` — tells uvicorn to find the `app` object inside `backend/main.py`
- `--reload` — automatically restarts the server when you save a file (great for development)
- `--host 127.0.0.1` — only accessible from your own machine (safe for development)
- `--port 8000` — the port number to listen on

### Step 5 — Expected Startup Output

```
============================================================
  Autonomous Research Agent  v1.0.0
  Environment : development
  Log Level   : INFO
  API Prefix  : /api/v1
  Docs        : http://127.0.0.1:8000/docs
============================================================
INFO     | backend.main | Server started successfully ✓
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

---

## 4. Viewing Outputs

### 4.1 — Root Endpoint

Open a browser or use `curl`:

```
http://127.0.0.1:8000/api/v1/
```

**Expected Response:**

```json
{
  "message": "Welcome to Autonomous Research Agent",
  "docs": "/docs",
  "version": "1.0.0"
}
```

### 4.2 — Health Check Endpoint

```
http://127.0.0.1:8000/api/v1/health
```

**Expected Response:**

```json
{
  "status": "healthy",
  "app_name": "Autonomous Research Agent",
  "version": "1.0.0",
  "environment": "development",
  "timestamp": "2026-07-03T05:16:31.704125"
}
```

This endpoint is designed for monitoring tools (like Render or Railway health checks) to confirm the server is alive.

### 4.3 — Swagger UI (Interactive Documentation)

```
http://127.0.0.1:8000/docs
```

Swagger UI is automatically generated by FastAPI. Here you can:
- See all available endpoints
- Read what each endpoint does (from our docstrings)
- Click **"Try it out"** to call any endpoint directly from the browser
- See the exact JSON schema for every response

### 4.4 — ReDoc (Alternative Documentation)

```
http://127.0.0.1:8000/redoc
```

A cleaner, read-only alternative to Swagger UI.

### 4.5 — Console Logs

When you make a request, you will see structured logs in the terminal:

```
INFO | backend.api.routes | Root endpoint called
INFO | backend.main       | → GET /api/v1/
INFO | backend.main       | ← GET /api/v1/ | 200 | 1.2ms
```

**Reading the log format:**

```
2026-07-03 10:30:00 | INFO     | module.name | message
     (1)               (2)          (3)           (4)
```

1. **Timestamp** — when it happened
2. **Log level** — severity (`DEBUG` < `INFO` < `WARNING` < `ERROR` < `CRITICAL`)
3. **Module name** — which file produced the log
4. **Message** — what happened

---

## 5. Concepts Behind the Implementation

### 5.1 — Pydantic Settings (Configuration Management)

**Problem:** In a naive implementation, every file reads from `.env` independently:

```python
# bad — repeated in every file
import os
API_KEY = os.getenv("GOOGLE_API_KEY")
```

**Solution:** Pydantic Settings creates a single validated configuration object:

```python
# backend/utils/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    google_api_key: str = ""
    tavily_api_key: str = ""
    log_level: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env")
```

Any file that needs a setting imports the singleton:

```python
from backend.utils.config import settings
print(settings.google_api_key)
```

**Benefits:**
- `.env` is read exactly once (cached with `@lru_cache`)
- Type validation catches mistakes early (e.g., `port` must be an integer)
- All settings are in one place — easy to find and change
- Auto-complete works in your IDE because types are explicit

### 5.2 — Structured Logging

**Problem:** Using `print()` for debugging:

```python
print("Searching...")         # No timestamp, no severity, no module name
print("ERROR: Search failed") # Looks like any other print
```

**Solution:** Python's `logging` module with a consistent format:

```python
logger.info("Planner agent started")
logger.warning("Rate limit approaching, slowing down")
logger.error("GitHub API returned 403 — check token")
```

The `get_logger(__name__)` pattern uses the module's own name as the logger name,
so you always know which file produced a log entry.

### 5.3 — API Versioning

Routes are mounted under `/api/v1/` instead of `/`:

```python
app.include_router(router, prefix=settings.api_prefix)  # /api/v1
```

**Why this matters:**
- You can release `/api/v2/` with breaking changes while `/api/v1/` still works for old clients
- Frontend and other consumers know exactly which version of the API they are using
- It is standard practice in production APIs

### 5.4 — Thin Controllers (Single Responsibility)

The route handlers in `routes.py` do the minimum — they validate input and return responses:

```python
@router.get("/health")
async def health_check() -> HealthResponse:
    logger.info("Health check endpoint called")
    return HealthResponse(
        status="healthy",
        app_name=settings.app_name,
        ...
    )
```

Business logic (running the AI agent, querying the database, generating PDFs) will live in
`services/`, `graph/`, `agents/` — **not** in routes. This keeps routes easy to read and test.

### 5.5 — Middleware

Two middleware functions wrap every request:

**CORS Middleware** — Allows the frontend (React app on port 5173) to call the backend
(on port 8000) without being blocked by the browser's security policy.

**Request Logging Middleware** — Automatically logs every request and its response time
without touching any route handler:

```python
@app.middleware("http")
async def request_logging_middleware(request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - start) * 1000
    logger.info(f"← {request.method} {request.url.path} | {response.status_code} | {elapsed_ms:.1f}ms")
    return response
```

### 5.6 — Lifespan Context Manager

FastAPI's modern way to handle startup and shutdown:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Code here runs on startup
    logger.info("Server started")
    yield                        # app is running here
    # Code here runs on shutdown
    logger.info("Shutting down")
```

This replaces the older `@app.on_event("startup")` pattern which is now deprecated.

### 5.7 — Pydantic Response Models

Every endpoint declares its return type:

```python
@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    ...
```

FastAPI uses `HealthResponse` to:
1. Validate that the response has the right structure
2. Automatically generate the Swagger schema
3. Strip any extra fields (security — prevents accidental data leaks)

---

## 6. Learning Notes

### Reading Order for New Learners

Start with these files in this order:

```
1. backend/utils/config.py      → Understand settings management
2. backend/utils/logger.py      → Understand logging setup
3. backend/schemas/responses.py → Understand response contracts
4. backend/api/routes.py        → Understand the endpoints
5. backend/main.py              → Understand how it all connects
```

### Key Questions to Ask While Reading

As you read each file, ask yourself:

- **config.py:** "Where does each setting come from? What happens if a key is missing?"
- **logger.py:** "Why does `_configure_root_logger()` check `if not root_logger.handlers`?"
- **routes.py:** "Why is there no database or AI logic here? Where will that go?"
- **main.py:** "What order does Python execute this file in? What runs at startup?"

### Common Beginner Mistakes to Avoid

| Mistake | Why It Is Bad | What to Do Instead |
|---|---|---|
| Reading `.env` in every file | Parsed multiple times, no validation | Import `settings` from `config.py` |
| Using `print()` for debugging | No timestamps, levels, or module info | Use `get_logger(__name__)` |
| Putting logic in route handlers | Hard to test, hard to reuse | Put logic in services/agents |
| Hardcoding values like ports | Breaks in different environments | Use `settings.port` |
| Creating a new `Settings()` each time | Reads `.env` every time | Use the cached `get_settings()` |

### How Functions Connect

```
Request arrives at uvicorn
        │
        ▼
request_logging_middleware (main.py)  ← logs the request
        │
        ▼
CORS Middleware (main.py)              ← checks origin header
        │
        ▼
Router (api/routes.py)                 ← matches the URL path
        │
        ▼
Route Handler (api/routes.py)          ← calls get_logger(), settings
        │
        ▼
Response Model (schemas/responses.py)  ← validates + shapes the JSON
        │
        ▼
request_logging_middleware (main.py)  ← logs the response time
        │
        ▼
Response sent back to client
```

### Testing Without a Browser

You can test endpoints from Python directly:

```python
import urllib.request
import json

# Test health endpoint
r = urllib.request.urlopen("http://127.0.0.1:8000/api/v1/health")
print(json.dumps(json.loads(r.read()), indent=2))
```

Or with `curl` in your terminal:

```bash
curl http://127.0.0.1:8000/api/v1/health
curl http://127.0.0.1:8000/api/v1/
```

### Understanding the `@lru_cache` Decorator

```python
@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
```

`@lru_cache` is Python's built-in memoization. The first call creates the `Settings` object
and reads `.env`. Every subsequent call returns the **same cached object** without reading `.env`
again. This is important because file I/O is slow and we do not want it happening on every request.

---

## 7. Next Steps — Phase 3 Preview

Phase 2 gives us a running server with zero AI logic. Phase 3 turns this into a **true autonomous agent** by adding:

### 7.1 — Agent State (`models/state.py`)

A shared Python `TypedDict` that flows through the entire LangGraph workflow:

```python
class AgentState(TypedDict):
    query: str
    research_plan: dict
    selected_tools: list[str]
    raw_results: list[dict]
    cleaned_corpus: str
    reflection: dict
    summary: dict
    iterations: int
    is_complete: bool
```

Every node in the graph reads from and writes to this state.

### 7.2 — LLM Service (`services/llm_service.py`)

A centralized service that all agents use to call Gemini:

```python
class LLMService:
    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(
            model=settings.gemini_model,
            google_api_key=settings.google_api_key,
        )
```

Without this, every agent would initialize its own LLM connection — wasteful and inconsistent.

### 7.3 — Prompt Management (`prompts/`)

Prompt templates stored as structured strings, not scattered inline:

```
prompts/
├── planner_prompt.py       ← "Given this query, create a research plan..."
├── reflection_prompt.py    ← "Have I collected enough information?..."
└── summarizer_prompt.py    ← "Generate a structured research report..."
```

### 7.4 — LangGraph Workflow (`graph/research_graph.py`)

The actual agent loop wired up as a directed graph:

```
START
  │
  ▼
planner_node          ← LLM decides research strategy
  │
  ▼
tool_selector_node    ← LLM chooses which tools to run
  │
  ▼
search_node           ← Tools run in parallel (asyncio.gather)
  │
  ▼
reflection_node       ← LLM decides: enough info? or search more?
  │                                         │
  │ (enough)                        (need more)
  ▼                                         │
summarizer_node ←─────────────────────────┘
  │
  ▼
END
```

### 7.5 — Connecting the Graph to the API

The `POST /api/v1/research` endpoint (currently a stub) will trigger the graph:

```python
@router.post("/research")
async def run_research(request: ResearchRequest) -> ResearchResponse:
    result = await research_graph.ainvoke({"query": request.query})
    return ResearchResponse(**result)
```

---

## Summary

Phase 2 is the **engineering foundation** — not the exciting AI part yet, but the part that
makes everything else maintainable, scalable, and production-quality.

| What we built | Why it matters |
|---|---|
| Centralized config | Secrets and settings managed safely |
| Structured logging | Every event is traceable with context |
| API versioning | Future-proof API contract |
| Thin controllers | Business logic is separate and testable |
| Response schemas | Self-documenting API with Swagger |
| Middleware | Cross-cutting concerns handled in one place |

> **Interview tip:** Be ready to explain *why* each piece exists, not just *what* it does.
> Interviewers love candidates who can articulate trade-offs and design decisions.

---

*Generated as part of the Autonomous Research Agent assessment project.*
*Phase 2 completion — July 2026*
