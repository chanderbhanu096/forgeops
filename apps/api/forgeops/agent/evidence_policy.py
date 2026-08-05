"""Deterministic evidence gates for trustworthy agent reports."""
from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

from forgeops.agent.context import MissionContext

_REPOSITORY_TERMS = (
    "repository",
    "repo",
    "codebase",
    "source code",
    "github.com/",
)


@dataclass(frozen=True)
class EvidenceGateResult:
    """Outcome of validating whether analysis may continue."""

    allowed: bool
    reason: str | None = None


def is_repository_analysis(ctx: MissionContext) -> bool:
    """Return whether the mission requests analysis of source code."""
    text = f"{ctx.title}\n{ctx.description}".lower()
    return any(term in text for term in _REPOSITORY_TERMS)


def has_valid_repository_url(repository_url: str | None) -> bool:
    """Validate a concrete HTTP(S) GitHub repository URL."""
    if not repository_url:
        return False
    parsed = urlparse(repository_url.strip())
    if parsed.scheme not in {"http", "https"} or parsed.netloc.lower() != "github.com":
        return False
    parts = [part for part in parsed.path.split("/") if part]
    return len(parts) >= 2


def validate_repository_target(ctx: MissionContext) -> EvidenceGateResult:
    """Require repository identity before a repository review proceeds."""
    if not is_repository_analysis(ctx):
        return EvidenceGateResult(allowed=True)
    if has_valid_repository_url(ctx.repository_url):
        return EvidenceGateResult(allowed=True)
    return EvidenceGateResult(
        allowed=False,
        reason=(
            "Repository analysis is blocked because no valid GitHub repository URL was "
            "identified. Add a URL such as https://github.com/owner/repository."
        ),
    )


def validate_retrieved_evidence(ctx: MissionContext) -> EvidenceGateResult:
    """Prevent hypotheses, patches and monitoring claims without source evidence."""
    if not is_repository_analysis(ctx):
        return EvidenceGateResult(allowed=True)
    sufficient = ctx.scratchpad.get("retrieval_sufficient") is True
    citations = ctx.scratchpad.get("retrieval_citations")
    has_citations = isinstance(citations, list) and any(str(item).strip() for item in citations)
    if ctx.raw_evidence and (sufficient or has_citations):
        return EvidenceGateResult(allowed=True)
    return EvidenceGateResult(
        allowed=False,
        reason=(
            "Repository analysis stopped safely because no verifiable source evidence was "
            "retrieved. No architecture findings, root cause, patch, test result or monitoring "
            "claim has been generated. Check GitHub access and retry."
        ),
    )
