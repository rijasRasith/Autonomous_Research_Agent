"""
Centralized configuration — all env vars are loaded once here.

Every other module should import `settings` from this file rather than
reading os.environ directly. Pydantic handles type validation automatically.
"""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",        # silently ignore unrecognised env vars
    )

    app_name: str = "Autonomous Research Agent"
    app_version: str = "1.0.0"
    app_env: Literal["development", "staging", "production"] = "development"
    debug: bool = True

    api_prefix: str = "/api/v1"
    host: str = "127.0.0.1"
    port: int = 8000

    google_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"

    tavily_api_key: str = ""
    max_search_results: int = 5

    database_url: str = "sqlite:///./research_memory.db"

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    log_format: str = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"

    # How many search → reflect cycles the agent is allowed before it must wrap up
    max_reflection_iterations: int = 3
    max_tool_timeout_seconds: int = 30

    reports_dir: str = "reports"


# lru_cache ensures Settings() is only instantiated once across the whole app —
# no redundant .env parsing on every import.
@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings: Settings = get_settings()
