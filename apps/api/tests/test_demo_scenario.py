"""Regression tests for the recruiter-facing demo scenario."""
from __future__ import annotations

import uuid

from forgeops.agent.context import MissionContext
from forgeops.agent.demo_scenario import demo_state_update
from forgeops.models.orm import AgentState


def _context() -> MissionContext:
    return MissionContext(
        mission_id=uuid.uuid4(),
        title="Investigate checkout failures",
        description="A simulated checkout incident.",
    )


def test_demo_scenario_populates_visible_report() -> None:
    ctx = _context()

    for state in (
        AgentState.environment_discovery,
        AgentState.plan_generation,
        AgentState.evidence_collection,
        AgentState.hypothesis_creation,
        AgentState.hypothesis_verification,
        AgentState.solution_generation,
        AgentState.sandbox_execution,
        AgentState.test_and_review,
        AgentState.execution,
        AgentState.post_action_monitoring,
    ):
        ctx.update(demo_state_update(state, ctx))

    checkpoint = ctx.to_checkpoint()
    scratchpad = checkpoint["scratchpad"]

    assert checkpoint["environment_summary"]
    assert len(checkpoint["plan"]) == 4
    assert len(checkpoint["hypotheses"]) == 3
    assert checkpoint["proposed_patch"]
    assert checkpoint["changed_files"] == ["apps/api/database.py"]
    assert checkpoint["test_passed"] is True
    assert scratchpad["retrieval_summary"]
    assert len(scratchpad["retrieval_citations"]) == 3
    assert scratchpad["agent_pipeline"]["confidence"] == 0.94
    assert scratchpad["monitoring"]["status"] == "healthy"
