"""
Memory routes — read agent memory and record feedback signals.
"""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from forgeops.db import get_db
from forgeops.memory.store import MemoryStore
from forgeops.models.orm import MemoryType

router = APIRouter()


class FeedbackRequest(BaseModel):
    mission_id: uuid.UUID
    feedback_type: str       # "patch_accepted" | "patch_rejected" | etc.
    outcome: str             # "positive" | "negative"
    detail: str


@router.get("/missions/{mission_id}", response_model=list[dict[str, Any]])
async def get_mission_memory(
    mission_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Return all memory entries for a specific mission."""
    store = MemoryStore(db)
    entries = await store.get_mission_memory(mission_id)
    return [
        {
            "id": str(e.id),
            "type": e.memory_type,
            "content": e.content,
            "extra": e.extra,
            "usefulness_score": e.usefulness_score,
            "created_at": e.created_at.isoformat(),
        }
        for e in entries
    ]


@router.get("/procedural", response_model=list[dict[str, Any]])
async def get_procedural_memory(
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Return the top procedural strategies ordered by usefulness."""
    store = MemoryStore(db)
    entries = await store.get_recent_procedural(limit=limit)
    return [
        {
            "id": str(e.id),
            "content": e.content,
            "extra": e.extra,
            "usefulness_score": e.usefulness_score,
        }
        for e in entries
    ]


@router.post("/feedback", status_code=200)
async def record_feedback(
    body: FeedbackRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Record a human feedback signal for a mission decision."""
    store = MemoryStore(db)
    entry = await store.record_feedback(
        mission_id=body.mission_id,
        feedback_type=body.feedback_type,
        outcome=body.outcome,
        detail=body.detail,
    )
    await db.commit()
    return {"id": str(entry.id), "status": "recorded"}


@router.post("/search", response_model=list[dict[str, Any]])
async def search_memory(
    query: str,
    memory_type: str | None = None,
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Text search over agent memory."""
    store = MemoryStore(db)
    types = [MemoryType(memory_type)] if memory_type else None
    entries = await store.search_by_text(query, memory_types=types, limit=limit)
    return [
        {
            "id": str(e.id),
            "type": e.memory_type,
            "content": e.content,
            "usefulness_score": e.usefulness_score,
            "similarity": e.similarity,
        }
        for e in entries
    ]
