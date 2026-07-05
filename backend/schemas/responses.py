# Yeh file health check aur error ke liye common response shapes banati hai jo API mein use hoti hain.

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
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
    message: str
    docs: str
    version: str


class ErrorResponse(BaseModel):
    error: str
    detail: Any = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
