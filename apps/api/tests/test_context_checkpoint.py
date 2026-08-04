"""Regression tests for recruiter-visible mission checkpoint data."""
from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest

from forgeops.agent.context import Hypothesis, MissionContext, PlanStep


@pytest.mark.asyncio
async def test_analysis_output_survives_checkpoint_reload() -> None:
    mission_id = uuid.uuid4()
    ctx = MissionContext(
        mission_id=mission_id,
        title="Review repository",
        description="Inspect a repository and report evidence.",
    )
    ctx.repository_url = "https://github.com/example/service"
    ctx.environment_summary = "FastAPI service with PostgreSQL."
    ctx.plan = [PlanStep(step_id="1", description="Inspect configuration")]
    ctx.add_evidence(
        source="apps/api/config.py",
        content="POOL_SIZE = 5",
        metadata={"citation": "config.py:12"},
    )
    ctx.relevant_files = ["apps/api/config.py"]
    ctx.log_excerpts = ["QueuePool timeout"]
    ctx.hypotheses = [
        Hypothesis(
            id="H1",
            description="The connection pool is undersized.",
            confidence=0.94,
            evidence=["config.py:12"],
        )
    ]
    ctx.top_hypothesis = ctx.hypotheses[0]
    ctx.proposed_patch = "--- a/config.py\n+++ b/config.py"
    ctx.changed_files = ["apps/api/config.py"]
    ctx.sandbox_test_output = "25/25 requests passed"
    ctx.test_passed = True
    ctx.scratchpad = {
        "retrieval_sufficient": True,
        "monitoring": {"status": "healthy", "observations": ["No timeouts"]},
    }

    mission = SimpleNamespace(
        id=mission_id,
        title=ctx.title,
        description=ctx.description,
        attachments=[],
        checkpoint=ctx.to_checkpoint(),
    )
    restored = await MissionContext.from_mission(mission)

    assert restored.repository_url == ctx.repository_url
    assert restored.raw_evidence == ctx.raw_evidence
    assert restored.relevant_files == ctx.relevant_files
    assert restored.log_excerpts == ctx.log_excerpts
    assert restored.top_hypothesis is not None
    assert restored.top_hypothesis.description == ctx.top_hypothesis.description
    assert restored.proposed_patch == ctx.proposed_patch
    assert restored.sandbox_test_output == ctx.sandbox_test_output
    assert restored.scratchpad["monitoring"]["status"] == "healthy"
