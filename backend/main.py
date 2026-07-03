"""
FastAPI entry point — wires everything together.

This file only creates the app, registers middleware and routes,
and handles startup/shutdown. No business logic should ever land here.

Run with:
    uvicorn backend.main:app --reload
"""

import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.api.routes import router
from backend.utils.config import settings
from backend.utils.logger import get_logger

logger = get_logger(__name__)


# Using lifespan instead of the old @app.on_event("startup") pattern —
# FastAPI deprecated those decorators in favour of this context manager approach.
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=" * 60)
    logger.info(f"  {settings.app_name}  v{settings.app_version}")
    logger.info(f"  Environment : {settings.app_env}")
    logger.info(f"  Log Level   : {settings.log_level}")
    logger.info(f"  API Prefix  : {settings.api_prefix}")
    logger.info(f"  Docs        : http://{settings.host}:{settings.port}/docs")
    logger.info("=" * 60)
    logger.info("Server started successfully ✓")

    yield  # app is running — everything between yield and end runs on shutdown

    logger.info("Server shutting down gracefully...")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "An autonomous AI research agent that plans, searches, reflects, "
        "and summarizes information using LangGraph + Gemini."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# allow_origins="*" is fine for local dev, but must be restricted before going to production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    # Wrapping every request so we get method, path, status code and response
    # time in a single log line — makes debugging in local dev much easier.
    start = time.perf_counter()
    logger.info(f"→ {request.method} {request.url.path}")
    try:
        response = await call_next(request)
    except Exception as exc:
        logger.error(f"Unhandled exception on {request.url.path}: {exc}")
        return JSONResponse(status_code=500, content={"error": "Internal server error"})
    elapsed_ms = (time.perf_counter() - start) * 1000
    logger.info(
        f"← {request.method} {request.url.path} | {response.status_code} | {elapsed_ms:.1f}ms"
    )
    return response


app.include_router(router, prefix=settings.api_prefix)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )
