"""Tests for the agent state machine runtime."""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from forgeops.agent.context import MissionContext, Hypothesis, PlanStep
from forgeops.agent.runtime import AgentRuntime, TRANSITIONS, InvalidTransitionError
from forgeops.models.orm import AgentState, Mission, MissionStatus


# ── Context tests ─────────────────────────────────────────────────────────────


def test_context_serialise_roundtrip():
    """MissionContext round-trips through to_checkpoint / _from_checkpoint."""
    mid = uuid.uuid4()
    ctx = MissionContext(
        mission_id=mid,
        title="Test mission",
        description="Investigate the pipeline",
    )
    ctx.plan = [PlanStep(step_id="s1", description="step one", skill_name="log_investigation")]
    ctx.hypotheses = [Hypothesis(id="h1", description="Column renamed", confidence=0.9, evidence=["log line"])]
    ctx.proposed_patch = "--- a/file.py\n+++ b/file.py\n@@ ...\n"

    checkpoint = ctx.to_checkpoint()

    # Reconstruct via a mock Mission
    mock_mission = MagicMock()
    mock_mission.id = mid
    mock_mission.title = ctx.title
    mock_mission.description = ctx.description
    mock_mission.attachments = []
    mock_mission.checkpoint = checkpoint

    restored = MissionContext._from_checkpoint(checkpoint, mock_mission)

    assert restored.mission_id == mid
    assert len(restored.plan) == 1
    assert restored.plan[0].step_id == "s1"
    assert len(restored.hypotheses) == 1
    assert restored.hypotheses[0].confidence == 0.9
    assert restored.proposed_patch is not None


def test_context_update_merges_keys():
    ctx = MissionContext(
        mission_id=uuid.uuid4(),
        title="T",
        description="D",
    )
    ctx.update({"repository_url": "https://github.com/example/repo", "test_passed": True})
    assert ctx.repository_url == "https://github.com/example/repo"
    assert ctx.test_passed is True


def test_context_update_ignores_unknown_keys():
    ctx = MissionContext(mission_id=uuid.uuid4(), title="T", description="D")
    ctx.update({"nonexistent_key": "value"})  # should not raise


# ── Transition table tests ────────────────────────────────────────────────────


def test_transitions_cover_all_states():
    """Every AgentState (except terminal ones) must have at least one successor."""
    terminal = {AgentState.completed, AgentState.failed}
    for state in AgentState:
        if state in terminal:
            assert TRANSITIONS.get(state, []) == [], f"{state} should have no transitions"
        else:
            assert state in TRANSITIONS, f"{state} missing from TRANSITIONS"
            assert len(TRANSITIONS[state]) >= 1, f"{state} has no successors"


def test_happy_path_is_contiguous():
    """The primary successor chain must connect mission_received → completed."""
    from forgeops.agent.runtime import TRANSITIONS

    visited = set()
    state = AgentState.mission_received
    while state != AgentState.completed:
        assert state not in visited, f"Cycle detected at {state}"
        visited.add(state)
        successors = [s for s in TRANSITIONS.get(state, []) if s != AgentState.failed]
        assert successors, f"Dead end at {state}"
        state = successors[0]


# ── Budget tests ──────────────────────────────────────────────────────────────


def test_budget_exceeded_error_raised():
    from forgeops.agent.runtime import BudgetExceededError
    raise_it = BudgetExceededError("Step budget exhausted")
    assert "Step budget" in str(raise_it)
