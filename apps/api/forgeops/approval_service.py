"""Shared helpers for durable human approval requests."""
from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from forgeops.agent.context import MissionContext
from forgeops.models.orm import Approval, ApprovalDecision, Mission


async def ensure_pending_approval(
    db: AsyncSession,
    mission: Mission,
    ctx: MissionContext | None = None,
) -> Approval:
    """Return the mission's pending approval, creating it when missing.

    The helper is intentionally idempotent. It is called by the runtime when a
    mission reaches the approval gate and by the API as a repair path for
    missions created before durable approval records were implemented.
    """
    result = await db.execute(
        select(Approval).where(
            Approval.mission_id == mission.id,
            Approval.decision == ApprovalDecision.pending,
        )
    )
    existing = result.scalar_one_or_none()
    if existing is not None:
        return existing

    context = ctx or await MissionContext.from_mission(mission)
    approval = Approval(
        mission_id=mission.id,
        summary=_summary(mission, context),
        diff=context.proposed_patch,
        evidence=_evidence(context),
        risk_level=_risk_level(context),
        decision=ApprovalDecision.pending,
    )
    db.add(approval)
    await db.commit()
    return approval


def _summary(mission: Mission, ctx: MissionContext) -> str:
    if ctx.top_hypothesis is not None:
        return (
            f"Approve the proposed action for '{mission.title}': "
            f"{ctx.top_hypothesis.description}"
        )
    if ctx.proposed_patch:
        return f"Approve the generated changes for '{mission.title}'"
    return f"Approve continuation of mission '{mission.title}'"


def _risk_level(ctx: MissionContext) -> str:
    severities = {
        str(item.get("severity", "")).strip().lower()
        for item in ctx.security_findings
        if isinstance(item, dict)
    }
    if severities & {"critical", "high"}:
        return "high"
    if ctx.proposed_patch and not ctx.test_passed:
        return "high"
    if ctx.proposed_patch:
        return "medium"
    return "low"


def _evidence(ctx: MissionContext) -> dict[str, Any]:
    hypothesis: dict[str, Any] | None = None
    if ctx.top_hypothesis is not None:
        hypothesis = {
            "id": ctx.top_hypothesis.id,
            "description": ctx.top_hypothesis.description,
            "confidence": ctx.top_hypothesis.confidence,
            "evidence": ctx.top_hypothesis.evidence,
        }

    return {
        "environment_summary": ctx.environment_summary,
        "top_hypothesis": hypothesis,
        "changed_files": ctx.changed_files,
        "test_passed": ctx.test_passed,
        "security_findings": ctx.security_findings,
    }
