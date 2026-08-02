"""Tests for multi-agent orchestration — unit tests using mocked agents."""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch

from forgeops.agent.multi_agent import (
    AgentPipelineResult,
    JudgeOutput,
    ReviewerOutput,
    SecurityOutput,
    MAX_REVISION_CYCLES,
    run_agent_pipeline,
)


# ── Unit tests for agent result types ─────────────────────────────────────────


def test_reviewer_output_approved():
    r = ReviewerOutput(approved=True, comments=["Looks good"], required_changes=[])
    assert r.approved
    assert r.required_changes == []


def test_reviewer_output_needs_changes():
    r = ReviewerOutput(
        approved=False,
        comments=[],
        required_changes=["Add a LIMIT clause", "Handle null values"],
    )
    assert not r.approved
    assert len(r.required_changes) == 2


def test_security_output_blocked():
    s = SecurityOutput(
        approved=False,
        findings=[{"severity": "critical", "title": "Hard-coded secret"}],
        blocked_by=["hard-coded secret"],
    )
    assert not s.approved
    assert s.blocked_by == ["hard-coded secret"]


def test_judge_output_structure():
    j = JudgeOutput(
        approved=True,
        summary="All checks passed. Ready for human review.",
        required_actions=[],
        confidence=0.95,
    )
    assert j.approved
    assert j.confidence == 0.95


def test_pipeline_result_structure():
    result = AgentPipelineResult(
        approved=True,
        patch="--- a/fix.py\n+++ b/fix.py\n",
        judge_summary="Patch verified.",
        revision_cycles=1,
        reviewer_comments=["Minor: consider adding a docstring"],
        security_findings=[],
        confidence=0.9,
    )
    assert result.approved
    assert result.revision_cycles == 1
    assert result.confidence == 0.9


# ── Integration tests with mocked LLM ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_pipeline_no_revision_needed():
    """When reviewer approves immediately, no builder revision should occur."""
    clean_patch = "--- a/models/revenue.sql\n+++ b/models/revenue.sql\n+amount / 100.0\n"

    with (
        patch("forgeops.agent.multi_agent.reviewer_agent") as mock_reviewer,
        patch("forgeops.agent.multi_agent.builder_agent") as mock_builder,
        patch("forgeops.agent.multi_agent.security_agent") as mock_security,
        patch("forgeops.agent.multi_agent.judge_agent") as mock_judge,
    ):
        mock_reviewer.return_value = ReviewerOutput(
            approved=True, comments=["Correct fix"], required_changes=[], confidence=0.9
        )
        mock_security.return_value = SecurityOutput(approved=True, findings=[])
        mock_judge.return_value = JudgeOutput(
            approved=True,
            summary="All good.",
            required_actions=[],
            confidence=0.92,
        )

        result = await run_agent_pipeline(
            patch=clean_patch,
            root_cause="Column renamed from eur to cents",
            sandbox_output="38/42 tests passed",
            repository_url="https://github.com/example/repo",
            verifier_summary="All checks passed",
        )

    assert result.approved
    assert result.revision_cycles == 0   # no revision needed
    mock_builder.assert_not_called()     # builder not invoked


@pytest.mark.asyncio
async def test_pipeline_one_revision_cycle():
    """When reviewer requests changes, builder should revise once."""
    original_patch = "--- a/fix.py\n+++ b/fix.py\n+x = 1\n"
    revised_patch = "--- a/fix.py\n+++ b/fix.py\n+x = 1  # with docstring\n"

    call_count = {"n": 0}

    async def mock_reviewer(**_):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return ReviewerOutput(
                approved=False,
                comments=[],
                required_changes=["Add a docstring"],
                confidence=0.6,
            )
        return ReviewerOutput(approved=True, comments=[], required_changes=[], confidence=0.9)

    with (
        patch("forgeops.agent.multi_agent.reviewer_agent", side_effect=mock_reviewer),
        patch("forgeops.agent.multi_agent.builder_agent", new_callable=AsyncMock) as mock_builder,
        patch("forgeops.agent.multi_agent.security_agent") as mock_security,
        patch("forgeops.agent.multi_agent.judge_agent") as mock_judge,
    ):
        mock_builder.return_value = revised_patch
        mock_security.return_value = SecurityOutput(approved=True, findings=[])
        mock_judge.return_value = JudgeOutput(
            approved=True, summary="Good.", required_actions=[], confidence=0.88
        )

        result = await run_agent_pipeline(
            patch=original_patch,
            root_cause="test",
            sandbox_output="",
            repository_url=None,
            verifier_summary="passed",
        )

    assert result.approved
    assert result.revision_cycles == 1
    mock_builder.assert_called_once()
    assert result.patch == revised_patch


@pytest.mark.asyncio
async def test_pipeline_security_block_propagates_to_judge():
    """Security findings must be passed to the judge who can then reject."""
    with (
        patch("forgeops.agent.multi_agent.reviewer_agent") as mock_reviewer,
        patch("forgeops.agent.multi_agent.builder_agent"),
        patch("forgeops.agent.multi_agent.security_agent") as mock_security,
        patch("forgeops.agent.multi_agent.judge_agent") as mock_judge,
    ):
        mock_reviewer.return_value = ReviewerOutput(
            approved=True, comments=[], required_changes=[], confidence=0.9
        )
        mock_security.return_value = SecurityOutput(
            approved=False,
            findings=[{"severity": "critical", "title": "Hardcoded API key"}],
            blocked_by=["hardcoded-secret"],
        )
        mock_judge.return_value = JudgeOutput(
            approved=False,
            summary="Blocked by security: hardcoded API key found.",
            required_actions=["Remove hardcoded API key"],
            confidence=0.99,
        )

        result = await run_agent_pipeline(
            patch="bad patch",
            root_cause="test",
            sandbox_output="",
            repository_url=None,
            verifier_summary="passed",
        )

    assert not result.approved
    assert len(result.security_findings) > 0


def test_max_revision_cycles_constant():
    """MAX_REVISION_CYCLES must be a sensible integer to prevent infinite loops."""
    assert isinstance(MAX_REVISION_CYCLES, int)
    assert 1 <= MAX_REVISION_CYCLES <= 10
