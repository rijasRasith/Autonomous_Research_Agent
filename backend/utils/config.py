# Yeh file saari app ki settings ek jagah se load karti hai — .env file padhti hai aur har jagah use hoti hai.

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

# Project root = two levels up from this file (backend/utils/config.py -> backend/ -> project root)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
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

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    log_format: str = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"

    max_reflection_iterations: int = 3
    max_tool_timeout_seconds: int = 120

    @property
    def database_url(self) -> str:
        """Always returns an absolute path so the DB is found regardless of CWD."""
        db_path = _PROJECT_ROOT / "research_memory.db"
        return f"sqlite:///{db_path.as_posix()}"

    @property
    def reports_dir(self) -> str:
        """Always returns an absolute path so reports are saved to the project root."""
        reports_path = _PROJECT_ROOT / "reports"
        reports_path.mkdir(parents=True, exist_ok=True)
        return str(reports_path)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings: Settings = get_settings()

