"""
API routes — all route handlers live here.

Handlers are kept thin on purpose: validate input, delegate to a service or
graph, and return a structured response. No business logic in this file.
"""

from datetime import datetime

from fastapi import APIRouter

from backend.schemas.responses import HealthResponse, RootResponse
from backend.utils.config import settings
from backend.utils.logger import get_logger

logger = get_logger(__name__)

# All routes here are automatically mounted under /api/v1 (see main.py)
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
    description="Returns service health status. Used by load balancers and monitoring.",
    tags=["System"],
)
async def health_check() -> HealthResponse:
    logger.info("Health check endpoint called")
    return HealthResponse(
        status="healthy",
        app_name=settings.app_name,
        version=settings.app_version,
        environment=settings.app_env,
        timestamp=datetime.utcnow(),
    )


# Research, history, and export routes will be added in later phases
# when the LangGraph pipeline and memory layer are ready.
