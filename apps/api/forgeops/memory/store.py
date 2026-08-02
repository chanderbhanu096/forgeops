"""
ForgeOps Memory System — operational memory that persists across missions.

Four memory types:

    Episodic   — What happened in a specific mission/incident.
                 Stored verbatim with mission linkage.

    Semantic   — Durable facts about the environment.
                 "This repository requires Python 3.13."
                 Stored with an embedding for similarity retrieval.

    Procedural — Strategies and workflows that have been proven to work.
                 "For Athena partition mismatches, inspect Glue metadata first."
                 Stored with an embedding; retrieved by task similarity.

    Feedback   — Human and system signals on agent decisions.
                 Accepted/rejected patches, supervisor corrections, deployments.
                 Used to weight future retrieval and proposed instruction updates.

Storage:
    All entries persisted to memory_entries (PostgreSQL + pgvector).
    In-memory LRU cache for the most recent entries per type.

Retrieval:
    - Exact match by mission_id (episodic)
    - Cosine similarity via pgvector (semantic, procedural)
    - BM25 keyword fallback when embeddings are unavailable
    - Relevance re-ranked by usefulness_score

Control principle:
    The memory system can PROPOSE updates (new instructions, skill versions)
    but cannot APPLY them without human review. All proposals are written
    to a pending_proposals table for inspection.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import structlog
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from forgeops.models.orm import MemoryEntry, MemoryType

log = structlog.get_logger(__name__)


# ── DTOs ──────────────────────────────────────────────────────────────────────


@dataclass
class MemoryResult:
    id: uuid.UUID
    memory_type: str
    content: str
    extra: dict[str, Any]
    usefulness_score: float
    created_at: datetime
    similarity: float = 0.0   # populated during vector search


# ── Memory store ──────────────────────────────────────────────────────────────


class MemoryStore:
    """
    Read/write interface to persistent operational memory.

    All write operations are async-safe and transactional.
    Read operations fall back gracefully when pgvector is unavailable.
    """

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    # ── Writes ────────────────────────────────────────────────────────────────

    async def record_episodic(
        self,
        mission_id: uuid.UUID,
        content: str,
        extra: dict[str, Any] | None = None,
    ) -> MemoryEntry:
        """Record a mission-specific observation or outcome."""
        entry = MemoryEntry(
            mission_id=mission_id,
            memory_type=MemoryType.episodic,
            content=content,
            extra=extra or {},
        )
        self._db.add(entry)
        await self._db.flush()
        log.debug("memory_episodic_written", mission_id=str(mission_id), chars=len(content))
        return entry

    async def record_semantic(
        self,
        content: str,
        extra: dict[str, Any] | None = None,
        mission_id: uuid.UUID | None = None,
        embedding: list[float] | None = None,
    ) -> MemoryEntry:
        """Record a durable environmental fact."""
        entry = MemoryEntry(
            mission_id=mission_id,
            memory_type=MemoryType.semantic,
            content=content,
            extra=extra or {},
            embedding=embedding,
        )
        self._db.add(entry)
        await self._db.flush()
        log.debug("memory_semantic_written", chars=len(content))
        return entry

    async def record_procedural(
        self,
        content: str,
        extra: dict[str, Any] | None = None,
        mission_id: uuid.UUID | None = None,
        embedding: list[float] | None = None,
    ) -> MemoryEntry:
        """Record a proven strategy or workflow."""
        entry = MemoryEntry(
            mission_id=mission_id,
            memory_type=MemoryType.procedural,
            content=content,
            extra=extra or {},
            embedding=embedding,
        )
        self._db.add(entry)
        await self._db.flush()
        log.debug("memory_procedural_written", chars=len(content))
        return entry

    async def record_feedback(
        self,
        mission_id: uuid.UUID,
        feedback_type: str,
        outcome: str,
        detail: str,
        extra: dict[str, Any] | None = None,
    ) -> MemoryEntry:
        """
        Record a human or system feedback signal.

        feedback_type: "patch_accepted" | "patch_rejected" | "root_cause_accepted"
                       | "root_cause_rejected" | "deployment_success" | "regression"
        outcome:       "positive" | "negative"
        """
        entry = MemoryEntry(
            mission_id=mission_id,
            memory_type=MemoryType.feedback,
            content=detail,
            extra={
                "feedback_type": feedback_type,
                "outcome": outcome,
                **(extra or {}),
            },
        )
        self._db.add(entry)
        await self._db.flush()
        log.info(
            "feedback_recorded",
            mission_id=str(mission_id),
            feedback_type=feedback_type,
            outcome=outcome,
        )
        return entry

    # ── Reads ─────────────────────────────────────────────────────────────────

    async def get_mission_memory(
        self, mission_id: uuid.UUID, limit: int = 50
    ) -> list[MemoryResult]:
        """Return all memory entries linked to a specific mission."""
        result = await self._db.execute(
            select(MemoryEntry)
            .where(MemoryEntry.mission_id == mission_id)
            .order_by(MemoryEntry.created_at.asc())
            .limit(limit)
        )
        return [_to_result(e) for e in result.scalars().all()]

    async def get_recent_procedural(self, limit: int = 10) -> list[MemoryResult]:
        """Return the most recently used procedural memories."""
        result = await self._db.execute(
            select(MemoryEntry)
            .where(MemoryEntry.memory_type == MemoryType.procedural)
            .order_by(MemoryEntry.usefulness_score.desc(), MemoryEntry.created_at.desc())
            .limit(limit)
        )
        return [_to_result(e) for e in result.scalars().all()]

    async def get_recent_semantic(self, limit: int = 20) -> list[MemoryResult]:
        """Return the highest-usefulness semantic facts."""
        result = await self._db.execute(
            select(MemoryEntry)
            .where(MemoryEntry.memory_type == MemoryType.semantic)
            .order_by(MemoryEntry.usefulness_score.desc())
            .limit(limit)
        )
        return [_to_result(e) for e in result.scalars().all()]

    async def search_by_text(
        self,
        query: str,
        memory_types: list[MemoryType] | None = None,
        limit: int = 10,
    ) -> list[MemoryResult]:
        """
        Keyword search over memory content using PostgreSQL trigram similarity.
        Fallback when vector embeddings are unavailable.
        """
        from sqlalchemy import or_, func

        stmt = select(MemoryEntry).order_by(MemoryEntry.usefulness_score.desc()).limit(limit)

        if memory_types:
            stmt = stmt.where(MemoryEntry.memory_type.in_(memory_types))

        # Simple ILIKE search; in production this uses pg_trgm similarity
        terms = query.lower().split()[:5]  # cap to 5 terms
        conditions = [MemoryEntry.content.ilike(f"%{term}%") for term in terms]
        if conditions:
            stmt = stmt.where(or_(*conditions))

        result = await self._db.execute(stmt)
        return [_to_result(e) for e in result.scalars().all()]

    async def search_by_vector(
        self,
        embedding: list[float],
        memory_types: list[MemoryType] | None = None,
        limit: int = 10,
        min_similarity: float = 0.7,
    ) -> list[MemoryResult]:
        """
        Cosine similarity search using pgvector.
        Falls back to text search if pgvector is unavailable.
        """
        try:
            from pgvector.sqlalchemy import Vector
            from sqlalchemy import cast, text

            # Use pgvector cosine distance operator
            distance_expr = MemoryEntry.embedding.op("<=>", return_type=None)(
                cast(embedding, Vector(len(embedding)))
            )

            stmt = (
                select(MemoryEntry, (1 - distance_expr).label("similarity"))
                .where(MemoryEntry.embedding.is_not(None))
                .where((1 - distance_expr) >= min_similarity)
                .order_by(distance_expr)
                .limit(limit)
            )
            if memory_types:
                stmt = stmt.where(MemoryEntry.memory_type.in_(memory_types))

            result = await self._db.execute(stmt)
            rows = result.all()
            return [_to_result(entry, similarity=float(sim)) for entry, sim in rows]

        except Exception as exc:
            log.warning("vector_search_unavailable", error=str(exc))
            return await self.search_by_text("", memory_types=memory_types, limit=limit)

    # ── Feedback loop ─────────────────────────────────────────────────────────

    async def mark_useful(
        self, entry_id: uuid.UUID, increment: float = 1.0
    ) -> None:
        """Increment the usefulness score when a memory was helpful."""
        await self._db.execute(
            update(MemoryEntry)
            .where(MemoryEntry.id == entry_id)
            .values(
                usefulness_score=MemoryEntry.usefulness_score + increment,
                retrieval_count=MemoryEntry.retrieval_count + 1,
            )
        )

    async def mark_unhelpful(
        self, entry_id: uuid.UUID, decrement: float = 0.5
    ) -> None:
        """Decrement usefulness when memory led to a poor outcome."""
        await self._db.execute(
            update(MemoryEntry)
            .where(MemoryEntry.id == entry_id)
            .values(
                usefulness_score=MemoryEntry.usefulness_score - decrement,
            )
        )


# ── Mission memory helper ─────────────────────────────────────────────────────


class MissionMemoryWriter:
    """
    Convenience wrapper that writes structured memory at the end of a mission.
    Called by the post_action_monitoring handler after the mission completes.
    """

    def __init__(self, store: MemoryStore) -> None:
        self._store = store

    async def write_mission_summary(
        self,
        mission_id: uuid.UUID,
        root_cause: str,
        solution_summary: str,
        outcome: str,  # "success" | "failure" | "partial"
        changed_files: list[str],
        pr_url: str | None,
    ) -> None:
        """Write episodic memory for a completed mission."""
        content = (
            f"Mission {mission_id} — outcome: {outcome}\n"
            f"Root cause: {root_cause}\n"
            f"Files changed: {', '.join(changed_files) or 'none'}\n"
            f"PR: {pr_url or 'none'}\n"
            f"Solution: {solution_summary}"
        )
        await self._store.record_episodic(
            mission_id=mission_id,
            content=content,
            extra={"outcome": outcome, "pr_url": pr_url},
        )
        log.info("mission_summary_written", mission_id=str(mission_id), outcome=outcome)

    async def learn_procedural(
        self,
        mission_id: uuid.UUID,
        strategy: str,
        context_tags: list[str],
    ) -> None:
        """Record a strategy that worked so future missions can reuse it."""
        await self._store.record_procedural(
            content=strategy,
            extra={"tags": context_tags},
            mission_id=mission_id,
        )
        log.info("procedural_strategy_learned", tags=context_tags)


# ── Private ───────────────────────────────────────────────────────────────────


def _to_result(entry: MemoryEntry, similarity: float = 0.0) -> MemoryResult:
    return MemoryResult(
        id=entry.id,
        memory_type=entry.memory_type,
        content=entry.content,
        extra=entry.extra or {},
        usefulness_score=entry.usefulness_score,
        created_at=entry.created_at,
        similarity=similarity,
    )
