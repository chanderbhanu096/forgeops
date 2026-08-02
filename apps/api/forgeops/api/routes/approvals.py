"""
Approval routes — human-in-the-loop decision endpoint.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from forgeops.db import get_db
from forgeops.models.orm import Approval, ApprovalDecision, Mission, MissionStatus

router = APIRouter()


class ApprovalDecisionRequest(BaseModel):
    decision: str       # "approved" | "rejected"
    reviewer_id: str
    notes: str | None = None


class ApprovalResponse(BaseModel):
    id: uuid.UUID
    mission_id: uuid.UUID
    summary: str
    diff: str | None
    risk_level: str
    decision: str
    created_at: datetime


@router.get("/pending", response_model=list[ApprovalResponse])
async def list_pending_approvals(
    db: AsyncSession = Depends(get_db),
) -> list[ApprovalResponse]:
    result = await db.execute(
        select(Approval)
        .where(Approval.decision == ApprovalDecision.pending)
        .order_by(Approval.created_at.asc())
    )
    return [
        ApprovalResponse(
            id=a.id,
            mission_id=a.mission_id,
            summary=a.summary,
            diff=a.diff,
            risk_level=a.risk_level,
            decision=a.decision,
            created_at=a.created_at,
        )
        for a in result.scalars().all()
    ]


@router.post("/{approval_id}/decide", status_code=status.HTTP_200_OK)
async def decide_approval(
    approval_id: uuid.UUID,
    body: ApprovalDecisionRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Record a human approval or rejection and resume the mission."""
    result = await db.execute(select(Approval).where(Approval.id == approval_id))
    approval = result.scalar_one_or_none()
    if approval is None:
        raise HTTPException(status_code=404, detail="Approval not found")

    if approval.decision != ApprovalDecision.pending:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Approval already decided: {approval.decision}",
        )

    if body.decision not in ("approved", "rejected"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="decision must be 'approved' or 'rejected'",
        )

    approval.decision = ApprovalDecision[body.decision]
    approval.reviewer_id = body.reviewer_id
    approval.reviewer_notes = body.notes
    approval.decided_at = datetime.now(timezone.utc)

    # Update mission status
    mission_result = await db.execute(
        select(Mission).where(Mission.id == approval.mission_id)
    )
    mission = mission_result.scalar_one_or_none()
    if mission:
        if body.decision == "approved":
            mission.status = MissionStatus.approved
            background_tasks.add_task(_resume_after_approval, mission.id)
        else:
            mission.status = MissionStatus.rejected

    await db.commit()
    return {"status": "ok"}


async def _resume_after_approval(mission_id: uuid.UUID) -> None:
    from forgeops.agent.runtime import AgentRuntime
    from forgeops.db import get_session_factory

    async with get_session_factory()() as db:
        runtime = AgentRuntime(db, mission_id)
        async for _event in runtime.resume_after_approval():
            pass
