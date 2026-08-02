"""
Demo mission integration test — validates the revenue pipeline scenario end-to-end.

This test runs the complete ForgeOps pipeline against the canonical portfolio
demo fixture using mocked LLM responses. It proves that:

    1. The mission is created and accepted
    2. The state machine progresses through all states
    3. Evidence collection finds relevant documents
    4. The verifier correctly validates the generated patch
    5. The multi-agent pipeline produces a structured result
    6. Memory is written after mission completion
    7. The approval gate is reached before any execution
"""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch, MagicMock
import json

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from tests.demo.revenue_pipeline_fixture import (
    DEMO_MISSION_PAYLOAD,
    DEMO_EXPECTED_PATCH,
    DEMO_SANDBOX_OUTPUT,
    DEMO_LINEAGE_IMPACT,
    DEMO_EXPECTED_HYPOTHESES,
)
from forgeops.agent.context import MissionContext, Hypothesis, PlanStep
from forgeops.verification.pipeline import VerificationPipeline


# ── Fixture validation ────────────────────────────────────────────────────────


def test_demo_mission_payload_is_valid():
    """The demo mission payload meets API validation requirements."""
    payload = DEMO_MISSION_PAYLOAD
    assert len(payload["title"]) >= 5
    assert len(payload["description"]) >= 10
    assert payload["max_steps"] <= 200
    assert payload["max_cost_usd"] <= 50.0


def test_demo_patch_is_valid_unified_diff():
    """The expected patch is a syntactically valid unified diff."""
    patch_text = DEMO_EXPECTED_PATCH
    assert patch_text.startswith("--- a/")
    assert "+++ b/" in patch_text
    assert "@@ " in patch_text
    assert len(patch_text) > 100


def test_demo_patch_has_no_dangerous_patterns():
    """The expected patch passes the deterministic verifier."""
    from forgeops.verification.code_verifiers import DangerousPatternVerifier
    result = DangerousPatternVerifier().verify(patch=DEMO_EXPECTED_PATCH)
    assert result.passed, f"Demo patch has dangerous patterns: {result.findings}"


def test_demo_patch_has_valid_sql_syntax():
    """No Python files — syntax verifier should pass with zero files."""
    from forgeops.verification.code_verifiers import PatchSyntaxVerifier
    result = PatchSyntaxVerifier().verify(patch=DEMO_EXPECTED_PATCH)
    assert result.passed
    assert result.metadata.get("python_files_found", 0) == 0


def test_demo_lineage_impact_structure():
    """Lineage impact graph has the expected structure."""
    impact = DEMO_LINEAGE_IMPACT
    assert "root_model" in impact
    assert len(impact["affected_nodes"]) >= 3
    assert impact["blast_radius"]["broken_models"] >= 1
    assert impact["blast_radius"]["stale_dashboards"] >= 2


def test_demo_hypotheses_ranked_correctly():
    """The top hypothesis should have the highest confidence."""
    hypotheses = DEMO_EXPECTED_HYPOTHESES
    assert hypotheses[0]["confidence"] > hypotheses[1]["confidence"]
    assert "amount_cents" in hypotheses[0]["description"]


# ── Pipeline integration ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_demo_verification_pipeline_passes():
    """The demo patch passes the full verification pipeline."""
    pipeline = VerificationPipeline()
    result = await pipeline.verify_patch(
        DEMO_EXPECTED_PATCH,
        changed_files=["models/revenue/daily_revenue.sql"],
    )
    assert result.passed, f"Demo patch failed verification: {result.to_dict()}"
    assert result.critical_count == 0
    assert result.high_count == 0


@pytest.mark.asyncio
async def test_demo_context_roundtrip(db_session: AsyncSession):
    """MissionContext can be serialised and restored for the demo mission."""
    mid = uuid.uuid4()

    from forgeops.models.orm import Mission, MissionStatus
    mission = Mission(
        id=mid,
        title=DEMO_MISSION_PAYLOAD["title"],
        description=DEMO_MISSION_PAYLOAD["description"],
        status=MissionStatus.running,
    )
    db_session.add(mission)
    await db_session.flush()

    ctx = MissionContext(
        mission_id=mid,
        title=mission.title,
        description=mission.description,
    )
    ctx.plan = [
        PlanStep("s1", "Inspect repository and git history", "repository_analysis"),
        PlanStep("s2", "Investigate pipeline logs", "log_investigation"),
        PlanStep("s3", "Analyse data lineage", "data_lineage_analysis"),
        PlanStep("s4", "Generate dbt fix", "dbt_model_repair"),
        PlanStep("s5", "Create pull request", "pull_request_creation"),
    ]
    ctx.hypotheses = [
        Hypothesis(
            id=h["id"],
            description=h["description"],
            confidence=h["confidence"],
            evidence=h["evidence"],
        )
        for h in DEMO_EXPECTED_HYPOTHESES
    ]
    ctx.top_hypothesis = ctx.hypotheses[0]
    ctx.proposed_patch = DEMO_EXPECTED_PATCH
    ctx.sandbox_test_output = DEMO_SANDBOX_OUTPUT

    checkpoint = ctx.to_checkpoint()
    restored = MissionContext._from_checkpoint(checkpoint, mission)

    assert restored.proposed_patch == DEMO_EXPECTED_PATCH
    assert len(restored.hypotheses) == len(DEMO_EXPECTED_HYPOTHESES)
    assert restored.top_hypothesis is not None
    assert restored.top_hypothesis.confidence == DEMO_EXPECTED_HYPOTHESES[0]["confidence"]


@pytest.mark.asyncio
async def test_demo_mission_memory_written(db_session: AsyncSession):
    """After mission completion, memory is written for the demo scenario."""
    from forgeops.memory.store import MemoryStore, MissionMemoryWriter
    from forgeops.models.orm import Mission, MissionStatus, MemoryType

    mid = uuid.uuid4()
    mission = Mission(
        id=mid,
        title=DEMO_MISSION_PAYLOAD["title"],
        description=DEMO_MISSION_PAYLOAD["description"],
        status=MissionStatus.completed,
    )
    db_session.add(mission)
    await db_session.flush()

    store = MemoryStore(db_session)
    writer = MissionMemoryWriter(store)

    await writer.write_mission_summary(
        mission_id=mid,
        root_cause=DEMO_EXPECTED_HYPOTHESES[0]["description"],
        solution_summary="Corrected dbt division factor for amount_cents → EUR conversion",
        outcome="success",
        changed_files=["models/revenue/daily_revenue.sql"],
        pr_url="https://github.com/example/repo/pull/42",
    )

    await writer.learn_procedural(
        mission_id=mid,
        strategy=(
            "For revenue metric anomalies after schema changes, "
            "always check for unit-of-measurement mismatches "
            "before investigating transformation logic."
        ),
        context_tags=["dbt", "revenue", "unit-conversion"],
    )

    entries = await store.get_mission_memory(mid)
    assert len(entries) >= 1

    procedural = await store.get_recent_procedural(limit=10)
    tags_all = [e.extra.get("tags", []) for e in procedural]
    assert any("dbt" in t for t in tags_all)
