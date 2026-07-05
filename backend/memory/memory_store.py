import hashlib
from datetime import datetime, timezone
from functools import lru_cache
from typing import Optional

from backend.database.models import ResearchMemory
from backend.database.session import SessionLocal
from backend.utils.logger import get_logger

logger = get_logger(__name__)


class MemoryStore:

    @staticmethod
    def _hash_query(query: str) -> str:
        normalized = query.lower().strip()
        return hashlib.sha256(normalized.encode()).hexdigest()

    def find(self, query: str) -> Optional[dict]:
        query_hash = self._hash_query(query)
        try:
            with SessionLocal() as session:
                record = session.query(ResearchMemory).filter_by(query_hash=query_hash).first()
                if not record:
                    return None
                age_hours = (datetime.now(timezone.utc) - record.created_at.replace(tzinfo=timezone.utc)).total_seconds() / 3600
                logger.info(f"[MemoryStore] Cache hit for hash {query_hash[:8]}... age={age_hours:.1f}h")
                return {
                    "id": record.id,
                    "query": record.query,
                    "summary": record.summary,
                    "tools_used": record.tools_used or [],
                    "iterations": record.iterations,
                    "sources_count": record.sources_count,
                    "export_paths": record.export_paths or {},
                    "created_at": record.created_at.isoformat(),
                    "age_hours": age_hours,
                }
        except Exception as exc:
            logger.error(f"[MemoryStore] find() failed: {exc}")
            return None

    def save(
        self,
        query: str,
        summary: dict,
        tools_used: list,
        iterations: int,
        sources_count: int,
        export_paths: dict,
    ) -> None:
        query_hash = self._hash_query(query)
        try:
            with SessionLocal() as session:
                existing = session.query(ResearchMemory).filter_by(query_hash=query_hash).first()
                if existing:
                    existing.summary = summary
                    existing.tools_used = tools_used
                    existing.iterations = iterations
                    existing.sources_count = sources_count
                    existing.export_paths = export_paths
                    existing.updated_at = datetime.now(timezone.utc)
                    logger.info(f"[MemoryStore] Updated record {query_hash[:8]}...")
                else:
                    record = ResearchMemory(
                        query=query,
                        query_hash=query_hash,
                        summary=summary,
                        tools_used=tools_used,
                        iterations=iterations,
                        sources_count=sources_count,
                        export_paths=export_paths,
                    )
                    session.add(record)
                    logger.info(f"[MemoryStore] Saved new record {query_hash[:8]}...")
                session.commit()
        except Exception as exc:
            logger.error(f"[MemoryStore] save() failed: {exc}")

    def get_all(self, limit: int = 20) -> list[dict]:
        try:
            with SessionLocal() as session:
                records = (
                    session.query(ResearchMemory)
                    .order_by(ResearchMemory.created_at.desc())
                    .limit(limit)
                    .all()
                )
                return [
                    {
                        "id": r.id,
                        "query": r.query,
                        "tools_used": r.tools_used or [],
                        "iterations": r.iterations,
                        "sources_count": r.sources_count,
                        "export_paths": r.export_paths or {},
                        "created_at": r.created_at.isoformat(),
                    }
                    for r in records
                ]
        except Exception as exc:
            logger.error(f"[MemoryStore] get_all() failed: {exc}")
            return []


@lru_cache(maxsize=1)
def get_memory_store() -> MemoryStore:
    return MemoryStore()
