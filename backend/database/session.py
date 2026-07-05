from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from backend.database.models import Base
from backend.utils.config import settings
from backend.utils.logger import get_logger

logger = get_logger(__name__)


@lru_cache(maxsize=1)
def _get_engine():
    url = settings.database_url
    logger.info(f"[DB] Connecting to: {url}")
    return create_engine(url, connect_args={"check_same_thread": False}, echo=False)


def _get_session_factory():
    return sessionmaker(autocommit=False, autoflush=False, bind=_get_engine())


class SessionLocal:
    """Proxy class to create sessions lazily from the deferred engine."""

    def __new__(cls) -> Session:  # type: ignore[override]
        return _get_session_factory()()

    @classmethod
    def __class_getitem__(cls, item):
        return _get_session_factory()().__class_getitem__(item)


# Support context manager usage: `with SessionLocal() as session:`
# The real session already supports that; we just ensure the factory is called lazily.


def init_db() -> None:
    logger.info("Initializing database tables...")
    Base.metadata.create_all(bind=_get_engine())
    logger.info("Database ready")

