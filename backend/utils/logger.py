# Yeh file logging setup karti hai — poori app mein ek hi jagah se logger milta hai, print use mat karo.

import logging
import sys
from functools import lru_cache

from backend.utils.config import settings


def _configure_root_logger() -> None:
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    console_handler = logging.StreamHandler(
        stream=open(sys.stdout.fileno(), mode="w", encoding="utf-8", buffering=1, closefd=False)
        if hasattr(sys.stdout, "fileno") and sys.stdout.fileno() >= 0
        else sys.stdout
    )
    console_handler.setLevel(log_level)

    formatter = logging.Formatter(
        fmt=settings.log_format,
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    if not root_logger.handlers:
        root_logger.addHandler(console_handler)

    for noisy_lib in ("httpx", "httpcore", "urllib3", "asyncio"):
        logging.getLogger(noisy_lib).setLevel(logging.WARNING)


_configure_root_logger()


@lru_cache(maxsize=128)
def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
