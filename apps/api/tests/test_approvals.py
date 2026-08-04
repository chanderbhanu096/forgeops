"""Tests for durable human approval requests."""
from __future__ import annotations

from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from forgeops.agent.context import MissionContext
from forgeops.agent.runtime import AgentRuntime, HANDLERS
from forgeops.approval_service import ensure_pending_approval
from forgeops.models.orm import AgentState, Approval, Mission, MissionStatus


@pytest.mark.asyncio
async def test_ensure_pending_approval_is_idempotent(
    db_session: AsyncSession,
) -> None:
    mission = Mission(
        title="Review generated deployment fix",
        description="Review a safe generated change before execution.",
        llm_provider="groq",
        llm_model="openai/gpt-oss-20b",
        status=MissionStatus.awaiting_approval,
        current_state=AgentState.human_approval,
        checkpoint={
            "title": "Review generated deployment fix",
            "description": "Review a safe generated change before execution.",
            "proposed_patch": "--- a/app.py\n+++ b/app.py\n@@ -1 +1 @@\n-old\n+new\n",
            "changed_files": ["app.py"],
            "test_passed": True,
        },
    )
    db_session.add(mission)
    await db_session.commit()

    first = await ensure_pending_approval(db_session, mission)
    second = await ensure_pending_approval(db_session, mission)

    count = await db_session.scalar(
        select(func.count()).select_from(Approval).where(
            Approval.mission_id == mission.id
        )
    )
    assert first.id == second.id
    assert count == 1
    assert first.diff is not None
    assert first.risk_level == "medium"


@pytest.mark.asyncio
async def test_pending_endpoint_repairs_orphaned_mission(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    mission = Mission(
        title="Orphaned approval mission",
        description="A mission created before approval records were persisted.",
        llm_provider="groq",
        llm_model="openai/gpt-oss-20b",
        status=MissionStatus.awaiting_approval,
        current_state=AgentState.human_approval,
        checkpoint={
            "title": "Orphaned approval mission",
            "description": "A mission created before approval records were persisted.",
            "changed_files": [],
            "test_passed": False,
        },
    )
    db_session.add(mission)
    await db_session.commit()

    response = await client.get("/api/v1/approvals/pending")

    assert response.status_code == 200
    assert any(item["mission_id"] == str(mission.id) for item in response.json())


@pytest.mark.asyncio
async def test_resume_after_approval_runs_execution_handler(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mission = Mission(
        title="Approved mission",
        description="Continue from the human approval gate.",
        llm_provider="groq",
        llm_model="openai/gpt-oss-20b",
        status=MissionStatus.approved,
        current_state=AgentState.human_approval,
        max_steps=10,
        checkpoint={
            "title": "Approved mission",
            "description": "Continue from the human approval gate.",
        },
    )
    db_session.add(mission)
    await db_session.commit()

    called: list[AgentState] = []

    async def fake_execution(
        _ctx: MissionContext,
        _db: AsyncSession,
    ) -> dict[str, Any]:
        called.append(AgentState.execution)
        return {}

    async def fake_monitoring(
        _ctx: MissionContext,
        _db: AsyncSession,
    ) -> dict[str, Any]:
        called.append(AgentState.post_action_monitoring)
        return {}

    monkeypatch.setitem(HANDLERS, AgentState.execution, fake_execution)
    monkeypatch.setitem(HANDLERS, AgentState.post_action_monitoring, fake_monitoring)

    runtime = AgentRuntime(db_session, mission.id)
    events = [event async for event in runtime.resume_after_approval()]

    assert called == [AgentState.execution, AgentState.post_action_monitoring]
    assert any(event["type"] == "completed" for event in events)
