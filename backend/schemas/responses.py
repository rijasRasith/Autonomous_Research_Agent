"""
Pydantic response schemas shared across all API endpoints.
FastAPI uses these to validate outgoing data and auto-generate the OpenAPI docs.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Response model for GET /health."""

    status: str = Field(default="healthy", description="Service health status")
    app_name: str = Field(..., description="Application name")
    version: str = Field(..., description="Application version")
    environment: str = Field(..., description="Deployment environment")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="UTC timestamp of the health check",
    )

    model_config = {"json_schema_extra": {"example": {
        "status": "healthy",
        "app_name": "Autonomous Research Agent",
        "version": "1.0.0",
        "environment": "development",
        "timestamp": "2025-01-01T00:00:00",
    }}}


class RootResponse(BaseModel):
    """Response model for GET /."""

    message: str
    docs: str
    version: str


class ErrorResponse(BaseModel):
    """Standard error envelope returned on 4xx / 5xx responses."""

    error: str
    # `detail` is Any because different errors carry different payloads —
    # a validation error may give a list of field issues, a 500 may give None.
    detail: Any = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
