"""
Mission routes — CRUD and execution control.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from forgeops.db import get_db
from forgeops.models.orm import Mission, MissionStatus

router = APIRouter()


# ── Request / response schemas ────────────────────────────────────────────────


class CreateMissionRequest(BaseModel):
    title: str = Field(..., min_length=5, max_length=500)
    description: str = Field(..., min_length=10)
    max_steps: int = Field(default=50, ge=1, le=200)
    max_cost_usd: float = Field(default=2.0, ge=0.01, le=50.0)
    attachments: list[dict[str, Any]] = Field(default_factory=list)


class MissionSummary(BaseModel):
    id: uuid.UUID
    title: str
    status: str
    current_state: str | None
    steps_used: int
    cost_usd_used: float
    created_at: datetime
    pull_request_url: str | None

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm(cls, m: Mission) -> "MissionSummary":
        result_data = m.result or {}
        return cls(
            id=m.id,
            title=m.title,
            status=m.status,
            current_state=m.current_state,
            steps_used=m.steps_used,
            cost_usd_used=m.cost_usd_used,
            created_at=m.created_at,
            pull_request_url=result_data.get("pull_request_url"),
        )


class MissionDetail(MissionSummary):
    description: str
    max_steps: int
    max_cost_usd: float
    checkpoint: dict[str, Any] | None = None
    result: dict[str, Any] | None = None
    error: str | None = None

    @classmethod
    def from_orm(cls, m: Mission) -> "MissionDetail":  # type: ignore[override]
        result_data = m.result or {}
        return cls(
            id=m.id,
            title=m.title,
            status=m.status,
            current_state=m.current_state,
            steps_used=m.steps_used,
            cost_usd_used=m.cost_usd_used,
            created_at=m.created_at,
            pull_request_url=result_data.get("pull_request_url"),
            description=m.description,
            max_steps=m.max_steps,
            max_cost_usd=m.max_cost_usd,
            checkpoint=m.checkpoint,
            result=m.result,
            error=m.error,
        )


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.post("", status_code=status.HTTP_201_CREATED, response_model=MissionDetail)
async def create_mission(
    body: CreateMissionRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> MissionDetail:
    """Create a new mission and immediately enqueue it for execution."""
    from forgeops.config import get_settings

    settings = get_settings()
    mission = Mission(
        title=body.title,
        description=body.description,
        max_steps=body.max_steps,
        max_cost_usd=body.max_cost_usd,
        max_duration_seconds=settings.default_max_duration_seconds,
        attachments=body.attachments,
        status=MissionStatus.pending,
    )
    db.add(mission)
    await db.commit()
    await db.refresh(mission)

    background_tasks.add_task(_run_mission, mission.id)
    return MissionDetail.from_orm(mission)


@router.get("", response_model=list[MissionSummary])
async def list_missions(
    db: AsyncSession = Depends(get_db),
    limit: int = 20,
    offset: int = 0,
) -> list[MissionSummary]:
    result = await db.execute(
        select(Mission).order_by(Mission.created_at.desc()).limit(limit).offset(offset)
    )
    return [MissionSummary.from_orm(m) for m in result.scalars().all()]


@router.get("/{mission_id}", response_model=MissionDetail)
async def get_mission(
    mission_id: uuid.UUID, db: AsyncSession = Depends(get_db)
) -> MissionDetail:
    mission = await _get_or_404(db, mission_id)
    return MissionDetail.from_orm(mission)


@router.post("/{mission_id}/pause", status_code=status.HTTP_200_OK)
async def pause_mission(
    mission_id: uuid.UUID, db: AsyncSession = Depends(get_db)
) -> dict[str, str]:
    mission = await _get_or_404(db, mission_id)
    if mission.status != MissionStatus.running:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Mission is {mission.status}, not running",
        )
    mission.status = MissionStatus.paused
    await db.commit()
    return {"status": "paused"}


@router.post("/{mission_id}/resume", status_code=status.HTTP_200_OK)
async def resume_mission(
    mission_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    mission = await _get_or_404(db, mission_id)
    if mission.status != MissionStatus.paused:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Mission is {mission.status}, not paused",
        )
    mission.status = MissionStatus.running
    await db.commit()
    background_tasks.add_task(_run_mission, mission.id)
    return {"status": "resumed"}


# ── Helpers ───────────────────────────────────────────────────────────────────


async def _get_or_404(db: AsyncSession, mission_id: uuid.UUID) -> Mission:
    result = await db.execute(select(Mission).where(Mission.id == mission_id))
    mission = result.scalar_one_or_none()
    if mission is None:
        raise HTTPException(status_code=404, detail="Mission not found")
    return mission


async def _run_mission(mission_id: uuid.UUID) -> None:
    """Background task: run the agent runtime for a mission."""
    from forgeops.agent.runtime import AgentRuntime
    from forgeops.db import get_session_factory

    async with get_session_factory()() as db:
        runtime = AgentRuntime(db, mission_id)
        async for _event in runtime.run():
            pass  # events are streamed via SSE — see sse.py
