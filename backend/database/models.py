from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.types import JSON


class Base(DeclarativeBase):
    pass


class ResearchMemory(Base):
    __tablename__ = "research_memory"

    id = Column(Integer, primary_key=True, autoincrement=True)
    query = Column(String(1000), nullable=False)
    query_hash = Column(String(64), unique=True, nullable=False, index=True)
    summary = Column(JSON, nullable=False)
    tools_used = Column(JSON, nullable=True)
    iterations = Column(Integer, default=1)
    sources_count = Column(Integer, default=0)
    export_paths = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
