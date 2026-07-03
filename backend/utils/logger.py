"""
Centralised logging setup for the whole application.

Call get_logger(__name__) in any module — never configure logging inline.
The root logger is configured once when this module is first imported.
"""

import logging
import sys
from functools import lru_cache

from backend.utils.config import settings


def _configure_root_logger() -> None:
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)

    formatter = logging.Formatter(
        fmt=settings.log_format,
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Avoid duplicate handlers on hot-reload
    if not root_logger.handlers:
        root_logger.addHandler(console_handler)

    # httpx and friends are very chatty by default — silencing them keeps
    # our own log output readable during development.
    for noisy_lib in ("httpx", "httpcore", "urllib3", "asyncio"):
        logging.getLogger(noisy_lib).setLevel(logging.WARNING)


_configure_root_logger()


@lru_cache(maxsize=128)
def get_logger(name: str) -> logging.Logger:
    """
    Returns a named logger. Usage:
        logger = get_logger(__name__)
        logger.info("Planner agent started")
    """
    return logging.getLogger(name)
