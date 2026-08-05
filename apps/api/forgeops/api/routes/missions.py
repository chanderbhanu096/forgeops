"""Mission routes — CRUD and execution control."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from forgeops.api.routes.models import list_model_providers
from forgeops.config import get_settings
from forgeops.db import get_db
from forgeops.models.orm import Mission, MissionStatus

router = APIRouter()


class CreateMissionRequest(BaseModel):
    title: str = Field(..., min_length=5, max_length=500)
    description: str = Field(..., min_length=10)
    max_steps: int = Field(default=50, ge=1, le=200)
    max_cost_usd: float = Field(default=2.0, ge=0.01, le=50.0)
    attachments: list[dict[str, Any]] = Field(default_factory=list)
    llm_provider: str | None = Field(default=None, min_length=2, max_length=50)
    llm_model: str | None = Field(default=None, min_length=1, max_length=200)


class MissionSummary(BaseModel):
    id: uuid.UUID
    title: str
    status: str
    current_state: str | None
    steps_used: int
    cost_usd_used: float
    created_at: datetime
    pull_request_url: str | None
    llm_provider: str
    llm_model: str

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm(cls, mission: Mission) -> MissionSummary:
        result_data = mission.result or {}
        return cls(
            id=mission.id,
            title=mission.title,
            status=mission.status,
            current_state=mission.current_state,
            steps_used=mission.steps_used,
            cost_usd_used=mission.cost_usd_used,
            created_at=mission.created_at,
            pull_request_url=result_data.get("pull_request_url"),
            llm_provider=mission.llm_provider,
            llm_model=mission.llm_model,
        )


class MissionDetail(MissionSummary):
    description: str
    max_steps: int
    max_cost_usd: float
    checkpoint: dict[str, Any] | None = None
    result: dict[str, Any] | None = None
    error: str | None = None

    @classmethod
    def from_orm(cls, mission: Mission) -> MissionDetail:  # type: ignore[override]
        result_data = mission.result or {}
        return cls(
            id=mission.id,
            title=mission.title,
            status=mission.status,
            current_state=mission.current_state,
            steps_used=mission.steps_used,
            cost_usd_used=mission.cost_usd_used,
            created_at=mission.created_at,
            pull_request_url=result_data.get("pull_request_url"),
            llm_provider=mission.llm_provider,
            llm_model=mission.llm_model,
            description=mission.description,
            max_steps=mission.max_steps,
            max_cost_usd=mission.max_cost_usd,
            checkpoint=mission.checkpoint,
            result=mission.result,
            error=mission.error,
        )


@router.post("", status_code=status.HTTP_201_CREATED, response_model=MissionDetail)
async def create_mission(
    body: CreateMissionRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> MissionDetail:
    """Create a mission using the selected provider/model and enqueue it."""
    settings = get_settings()
    provider_id = (body.llm_provider or settings.default_llm_provider).strip().lower()
    model_id = (body.llm_model or settings.default_llm_model).strip()

    catalog = await list_model_providers()
    provider = next((entry for entry in catalog.providers if entry.id == provider_id), None)
    if provider is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unknown LLM provider: {provider_id}",
        )
    if not provider.configured:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Provider '{provider.label}' is not configured. "
                f"{provider.configuration_hint}"
            ),
        )
    if not model_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A model ID is required.",
        )
    if not provider.supports_custom_model and model_id not in provider.models:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Model '{model_id}' is not supported by {provider.label}.",
        )

    mission = Mission(
        title=body.title,
        description=body.description,
        max_steps=body.max_steps,
        max_cost_usd=body.max_cost_usd,
        max_duration_seconds=settings.default_max_duration_seconds,
        attachments=body.attachments,
        status=MissionStatus.pending,
        llm_provider=provider_id,
        llm_model=model_id,
    )
    db.add(mission)
    await db.commit()
    await db.refresh(mission)

    background_tasks.add_task(_run_mission, mission.id)
    return MissionDetail.from_orm(mission)


@router.get("", response_model=list[MissionSummary])
async def list_missions(
    db: AsyncSession = Depends(get_db),  # noqa: B008
    limit: int = 20,
    offset: int = 0,
) -> list[MissionSummary]:
    result = await db.execute(
        select(Mission).order_by(Mission.created_at.desc()).limit(limit).offset(offset)
    )
    return [MissionSummary.from_orm(mission) for mission in result.scalars().all()]


@router.get("/{mission_id}", response_model=MissionDetail)
async def get_mission(
    mission_id: uuid.UUID, db: AsyncSession = Depends(get_db)  # noqa: B008
) -> MissionDetail:
    mission = await _get_or_404(db, mission_id)
    return MissionDetail.from_orm(mission)


@router.post("/{mission_id}/pause", status_code=status.HTTP_200_OK)
async def pause_mission(
    mission_id: uuid.UUID, db: AsyncSession = Depends(get_db)  # noqa: B008
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
    db: AsyncSession = Depends(get_db),  # noqa: B008
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


async def _get_or_404(db: AsyncSession, mission_id: uuid.UUID) -> Mission:
    result = await db.execute(select(Mission).where(Mission.id == mission_id))
    mission = result.scalar_one_or_none()
    if mission is None:
        raise HTTPException(status_code=404, detail="Mission not found")
    return mission


async def _run_mission(mission_id: uuid.UUID) -> None:
    """Run the agent and publish every state event to the mission SSE channel."""
    from forgeops.agent.runtime import AgentRuntime
    from forgeops.api.routes.sse import publish_event
    from forgeops.db import get_session_factory

    async with get_session_factory()() as db:
        runtime = AgentRuntime(db, mission_id)
        async for event in runtime.run():
            event_type = str(event.get("type", "state_changed"))
            event_data = event.get("data", {})
            if not isinstance(event_data, dict):
                event_data = {"value": event_data}
            await publish_event(mission_id, event_type, event_data)
