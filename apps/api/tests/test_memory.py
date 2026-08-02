"""Tests for the memory system."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from forgeops.memory.store import MemoryStore, MissionMemoryWriter, MemoryResult
from forgeops.models.orm import MemoryType


# ── MemoryStore writes ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_record_episodic(db_session: AsyncSession) -> None:
    store = MemoryStore(db_session)
    mid = uuid.uuid4()
    entry = await store.record_episodic(
        mission_id=mid,
        content="Pipeline failed due to column rename",
        extra={"pipeline": "revenue"},
    )
    assert entry.id is not None
    assert entry.memory_type == MemoryType.episodic
    assert entry.content == "Pipeline failed due to column rename"


@pytest.mark.asyncio
async def test_record_semantic(db_session: AsyncSession) -> None:
    store = MemoryStore(db_session)
    entry = await store.record_semantic(
        content="This repository requires Python 3.12",
        extra={"source": "pyproject.toml"},
    )
    assert entry.memory_type == MemoryType.semantic


@pytest.mark.asyncio
async def test_record_procedural(db_session: AsyncSession) -> None:
    store = MemoryStore(db_session)
    entry = await store.record_procedural(
        content=(
            "For Athena partition mismatches, inspect Glue metadata "
            "before modifying the transformation."
        )
    )
    assert entry.memory_type == MemoryType.procedural


@pytest.mark.asyncio
async def test_record_feedback(db_session: AsyncSession) -> None:
    store = MemoryStore(db_session)
    mid = uuid.uuid4()

    # Need a mission row first for FK constraint
    from forgeops.models.orm import Mission, MissionStatus
    mission = Mission(
        id=mid,
        title="Test mission",
        description="test",
        status=MissionStatus.completed,
    )
    db_session.add(mission)
    await db_session.flush()

    entry = await store.record_feedback(
        mission_id=mid,
        feedback_type="patch_accepted",
        outcome="positive",
        detail="Reviewer approved the revenue fix patch",
    )
    assert entry.memory_type == MemoryType.feedback
    assert entry.extra["feedback_type"] == "patch_accepted"
    assert entry.extra["outcome"] == "positive"


# ── MemoryStore reads ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_mission_memory_returns_entries(db_session: AsyncSession) -> None:
    store = MemoryStore(db_session)
    mid = uuid.uuid4()

    from forgeops.models.orm import Mission, MissionStatus
    mission = Mission(id=mid, title="T", description="D", status=MissionStatus.completed)
    db_session.add(mission)
    await db_session.flush()

    await store.record_episodic(mid, "Event 1")
    await store.record_episodic(mid, "Event 2")

    results = await store.get_mission_memory(mid)
    assert len(results) == 2
    contents = [r.content for r in results]
    assert "Event 1" in contents
    assert "Event 2" in contents


@pytest.mark.asyncio
async def test_search_by_text_returns_matching_entries(db_session: AsyncSession) -> None:
    store = MemoryStore(db_session)
    await store.record_semantic(content="revenue pipeline column rename caused failure")
    await store.record_semantic(content="unrelated database optimisation tip")

    results = await store.search_by_text("revenue pipeline", memory_types=[MemoryType.semantic])
    assert len(results) >= 1
    assert any("revenue" in r.content.lower() for r in results)


@pytest.mark.asyncio
async def test_get_recent_procedural(db_session: AsyncSession) -> None:
    store = MemoryStore(db_session)
    await store.record_procedural("Strategy A for dbt failures")
    await store.record_procedural("Strategy B for Athena issues")

    results = await store.get_recent_procedural(limit=10)
    assert len(results) >= 2


# ── MissionMemoryWriter ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_mission_memory_writer_summary(db_session: AsyncSession) -> None:
    from forgeops.models.orm import Mission, MissionStatus

    mid = uuid.uuid4()
    mission = Mission(id=mid, title="T", description="D", status=MissionStatus.completed)
    db_session.add(mission)
    await db_session.flush()

    store = MemoryStore(db_session)
    writer = MissionMemoryWriter(store)
    await writer.write_mission_summary(
        mission_id=mid,
        root_cause="Column renamed from revenue_usd to revenue_eur",
        solution_summary="Updated dbt conversion multiplier",
        outcome="success",
        changed_files=["models/daily_revenue.sql"],
        pr_url="https://github.com/example/repo/pull/42",
    )

    entries = await store.get_mission_memory(mid)
    assert len(entries) == 1
    assert "revenue_usd" in entries[0].content
    assert "success" in entries[0].content


@pytest.mark.asyncio
async def test_mission_memory_writer_learns_strategy(db_session: AsyncSession) -> None:
    from forgeops.models.orm import Mission, MissionStatus

    mid = uuid.uuid4()
    mission = Mission(id=mid, title="T", description="D", status=MissionStatus.completed)
    db_session.add(mission)
    await db_session.flush()

    store = MemoryStore(db_session)
    writer = MissionMemoryWriter(store)
    await writer.learn_procedural(
        mission_id=mid,
        strategy="For currency conversion bugs, always check the source system unit before the transform",
        context_tags=["dbt", "revenue"],
    )

    procedural = await store.get_recent_procedural(limit=10)
    tags = [e.extra.get("tags", []) for e in procedural]
    assert any("dbt" in t for t in tags)
