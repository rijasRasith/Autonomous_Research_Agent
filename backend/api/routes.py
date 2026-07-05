import time
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from backend.graph.research_graph import get_research_graph
from backend.memory.memory_store import get_memory_store
from backend.schemas.research import (
    HistoryItem,
    ResearchRequest,
    ResearchResponse,
    ResearchSummary,
)
from backend.schemas.responses import HealthResponse, RootResponse
from backend.utils.config import settings
from backend.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.get(
    "/",
    response_model=RootResponse,
    summary="Root",
    description="API entry point — confirms the service is reachable.",
    tags=["System"],
)
async def root() -> RootResponse:
    logger.info("Root endpoint called")
    return RootResponse(
        message=f"Welcome to {settings.app_name}",
        docs="/docs",
        version=settings.app_version,
    )


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health Check",
    description="Returns service health status.",
    tags=["System"],
)
async def health_check() -> HealthResponse:
    logger.info("Health check endpoint called")
    return HealthResponse(
        status="healthy",
        app_name=settings.app_name,
        version=settings.app_version,
        environment=settings.app_env,
        timestamp=datetime.now(timezone.utc),
    )


@router.post(
    "/research",
    response_model=ResearchResponse,
    summary="Run Autonomous Research",
    description=(
        "Runs the full autonomous agent loop: "
        "memory_check -> planner -> tool_selector -> search -> reflect -> summarize -> export -> memory_save. "
        "Returns a structured research report with download paths."
    ),
    tags=["Research"],
)
async def run_research(request: ResearchRequest) -> ResearchResponse:
    logger.info(f"Research request | query={request.query!r} | force_refresh={request.force_refresh}")
    start_time = time.perf_counter()

    try:
        graph = get_research_graph()

        initial_state: dict = {
            "query": request.query,
            "raw_results": [],
            "warnings": [],
            "force_refresh": request.force_refresh,
        }

        final_state = await graph.ainvoke(initial_state)

        elapsed = time.perf_counter() - start_time
        summary_raw = final_state.get("summary", {})
        error = final_state.get("error")
        memory_hit = final_state.get("memory_hit", False)

        if error and not summary_raw:
            raise HTTPException(status_code=500, detail=error)

        summary = None
        if summary_raw:
            try:
                summary = ResearchSummary(
                    executive_summary=summary_raw.get("executive_summary", ""),
                    key_points=summary_raw.get("key_points", []),
                    important_findings=summary_raw.get("important_findings", []),
                    references=summary_raw.get("references", []),
                    actionable_insights=summary_raw.get("actionable_insights", []),
                )
            except Exception as parse_err:
                logger.warning(f"Summary parse warning: {parse_err}")

        raw_results = final_state.get("raw_results", [])
        status = "cached" if memory_hit else ("completed" if not error else "completed_with_warnings")

        logger.info(
            f"Research done | elapsed={elapsed:.1f}s | sources={len(raw_results)} | "
            f"iterations={final_state.get('iteration_count', 1)} | memory_hit={memory_hit}"
        )

        return ResearchResponse(
            query=request.query,
            status=status,
            summary=summary,
            tools_used=final_state.get("selected_tools", []),
            iterations=final_state.get("iteration_count", 1),
            sources_count=len(raw_results),
            export_paths=final_state.get("export_paths", {}),
            memory_hit=memory_hit,
            error=error,
            timestamp=datetime.now(timezone.utc),
            processing_time_seconds=round(elapsed, 2),
        )

    except HTTPException:
        raise
    except Exception as exc:
        elapsed = time.perf_counter() - start_time
        logger.error(f"Research failed | query={request.query!r} | error={exc}")
        raise HTTPException(
            status_code=500,
            detail=f"Research agent encountered an error: {str(exc)}",
        )


@router.get(
    "/research/history",
    response_model=list[HistoryItem],
    summary="Get Research History",
    description="Returns the 20 most recent research queries stored in memory.",
    tags=["Research"],
)
async def get_history() -> list[HistoryItem]:
    store = get_memory_store()
    records = store.get_all(limit=20)
    return [HistoryItem(**r) for r in records]


@router.get(
    "/research/download/{filename}",
    summary="Download Report File",
    description="Download a generated Markdown or PDF report by its filename.",
    tags=["Research"],
)
async def download_report(filename: str) -> FileResponse:
    safe_name = Path(filename).name
    filepath = Path(settings.reports_dir) / safe_name

    if not filepath.exists():
        raise HTTPException(status_code=404, detail=f"Report not found: {safe_name}")

    media_type = "application/pdf" if filepath.suffix.lower() == ".pdf" else "text/markdown"

    return FileResponse(path=str(filepath), filename=safe_name, media_type=media_type)
