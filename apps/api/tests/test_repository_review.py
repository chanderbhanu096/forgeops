"""Regression tests for evidence-backed repository overview missions."""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

import pytest

from forgeops.agent.context import MissionContext
from forgeops.agent.repository_review import (
    handle_environment_discovery,
    handle_plan_generation,
)
from forgeops.agent.runtime import AgentRuntime
from forgeops.integrations.github_repository import (
    GitHubRepositoryClient,
    normalise_github_repository_url,
    parse_github_repository_url,
)
from forgeops.models.orm import AgentState


EXACT_PROMPT = (
    "https://github.com/chanderbhanu096/rewardlens-fraud-decision-lab.git "
    "INVESTIGATE THIS REPOS AND GIVE ME OVERVIEW"
)


def _context() -> MissionContext:
    return MissionContext(
        mission_id=uuid.uuid4(),
        title="RewardLens repository overview",
        description=EXACT_PROMPT,
    )


def test_parse_github_repository_url_removes_git_suffix() -> None:
    assert parse_github_repository_url(
        "https://github.com/chanderbhanu096/rewardlens-fraud-decision-lab.git"
    ) == ("chanderbhanu096", "rewardlens-fraud-decision-lab")
    assert normalise_github_repository_url(
        "https://github.com/chanderbhanu096/rewardlens-fraud-decision-lab.git"
    ) == "https://github.com/chanderbhanu096/rewardlens-fraud-decision-lab"


@pytest.mark.asyncio
async def test_exact_prompt_is_resolved_without_model_tool_call() -> None:
    ctx = _context()
    result = await handle_environment_discovery(ctx, AsyncMock())

    assert result["repository_url"] == (
        "https://github.com/chanderbhanu096/rewardlens-fraud-decision-lab"
    )
    assert result["scratchpad"]["mission_mode"] == "repository_overview"
    assert "Source-backed inspection" not in result["environment_summary"]
    assert "pin all findings to a commit" in result["environment_summary"]


@pytest.mark.asyncio
async def test_repository_overview_plan_is_deterministic() -> None:
    ctx = _context()
    ctx.scratchpad["mission_mode"] = "repository_overview"
    result = await handle_plan_generation(ctx, AsyncMock())

    assert len(result["plan"]) == 4
    assert all(step.skill_name for step in result["plan"])
    assert "commit SHA" in result["plan"][0].description


def test_repository_overview_completes_after_evidence_collection() -> None:
    ctx = _context()
    ctx.scratchpad["mission_mode"] = "repository_overview"
    runtime = AgentRuntime(AsyncMock(), ctx.mission_id)

    assert runtime._next_runnable_state(AgentState.evidence_collection, ctx) == (
        AgentState.completed
    )


def test_relevant_file_selection_never_selects_empty_path() -> None:
    entries = [
        {"type": "blob", "path": "README.md", "size": 100},
        {"type": "blob", "path": "src/main.py", "size": 200},
        {"type": "blob", "path": "assets/logo.png", "size": 300},
    ]
    selected = GitHubRepositoryClient._select_paths(
        entries,
        EXACT_PROMPT,
        max_files=10,
    )

    assert [item["path"] for item in selected] == ["README.md", "src/main.py"]
    assert all(str(item["path"]).strip() for item in selected)
