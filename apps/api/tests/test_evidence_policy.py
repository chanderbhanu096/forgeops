from __future__ import annotations

import uuid

from forgeops.agent.context import MissionContext
from forgeops.agent.evidence_policy import (
    has_valid_repository_url,
    is_repository_analysis,
    validate_repository_target,
    validate_retrieved_evidence,
)


def make_context(description: str) -> MissionContext:
    return MissionContext(
        mission_id=uuid.uuid4(),
        title="Engineering review",
        description=description,
    )


def test_detects_repository_analysis() -> None:
    ctx = make_context("Review https://github.com/example/service and identify risks")
    assert is_repository_analysis(ctx) is True


def test_validates_github_repository_urls() -> None:
    assert has_valid_repository_url("https://github.com/example/service") is True
    assert has_valid_repository_url("https://example.com/example/service") is False
    assert has_valid_repository_url(None) is False


def test_repository_target_blocks_missing_url() -> None:
    ctx = make_context("Review this repository and identify the biggest risks")
    result = validate_repository_target(ctx)
    assert result.allowed is False
    assert "valid GitHub repository URL" in str(result.reason)


def test_evidence_gate_blocks_unverified_report() -> None:
    ctx = make_context("Review https://github.com/example/service")
    ctx.repository_url = "https://github.com/example/service"
    ctx.scratchpad["retrieval_sufficient"] = False
    result = validate_retrieved_evidence(ctx)
    assert result.allowed is False
    assert "no verifiable source evidence" in str(result.reason)


def test_evidence_gate_allows_cited_evidence() -> None:
    ctx = make_context("Review https://github.com/example/service")
    ctx.repository_url = "https://github.com/example/service"
    ctx.add_evidence(
        source="README.md",
        content="A documented service",
        metadata={"citation": "README.md:1-5"},
    )
    ctx.scratchpad.update(
        {
            "retrieval_sufficient": True,
            "retrieval_citations": ["README.md:1-5"],
        }
    )
    assert validate_retrieved_evidence(ctx).allowed is True
