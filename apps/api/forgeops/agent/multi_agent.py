"""
Multi-agent orchestration — structured agent pipeline for code review.

The pipeline is a linear sequence with clear, non-overlapping responsibilities:

    Builder → Reviewer → Builder (revise) → Security → Verifier → Judge

Each agent is a pure async function that receives context and returns
a structured result. The orchestrator drives the loop and decides
whether to continue iterating or proceed to the approval gate.

Maximum revision cycles are capped to prevent infinite loops.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

import structlog

from forgeops.agent.gateway import ModelGateway

log = structlog.get_logger(__name__)
_gateway = ModelGateway()

MAX_REVISION_CYCLES = 3


# ── Result types ──────────────────────────────────────────────────────────────


@dataclass
class ReviewerOutput:
    approved: bool
    comments: list[str]
    required_changes: list[str]
    confidence: float = 0.8


@dataclass
class SecurityOutput:
    approved: bool
    findings: list[dict[str, str]]
    blocked_by: list[str] = field(default_factory=list)


@dataclass
class VerifierOutput:
    passed: bool
    test_results: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)


@dataclass
class JudgeOutput:
    approved: bool
    summary: str
    required_actions: list[str]
    confidence: float


@dataclass
class AgentPipelineResult:
    """Final result returned to the runtime after the multi-agent pipeline."""
    approved: bool
    patch: str
    judge_summary: str
    revision_cycles: int
    reviewer_comments: list[str]
    security_findings: list[dict[str, str]]
    confidence: float


# ── Agent functions ───────────────────────────────────────────────────────────


async def reviewer_agent(
    patch: str,
    root_cause: str,
    sandbox_output: str,
    prior_comments: list[str],
) -> ReviewerOutput:
    """
    Reviewer agent — checks logical correctness, test coverage and maintainability.
    Returns specific change requests if the patch is not yet acceptable.
    """
    prior_context = (
        f"\nPrior review comments addressed:\n" + "\n".join(f"- {c}" for c in prior_comments)
        if prior_comments
        else ""
    )

    messages = [
        {
            "role": "system",
            "content": (
                "You are a principal data engineer reviewing a code patch. "
                "Your job: verify that the patch correctly addresses the root cause, "
                "has adequate test coverage, and introduces no regressions. "
                "Be specific. Request only necessary changes."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Root cause: {root_cause}\n"
                f"Sandbox output: {sandbox_output or 'not available'}\n"
                f"{prior_context}\n\n"
                f"Patch:\n{patch[:4000]}\n\n"
                "Return JSON:\n"
                "  approved: bool\n"
                "  comments: list[string]  (observations, not blockers)\n"
                "  required_changes: list[string]  (blockers — empty if approved)\n"
                "  confidence: float (0.0-1.0)"
            ),
        },
    ]

    response = await _gateway.chat(messages, response_format={"type": "json_object"})
    try:
        data = json.loads(response.content)
    except json.JSONDecodeError:
        data = {}

    return ReviewerOutput(
        approved=bool(data.get("approved", True)),
        comments=data.get("comments", []),
        required_changes=data.get("required_changes", []),
        confidence=float(data.get("confidence", 0.7)),
    )


async def builder_agent(
    original_patch: str,
    root_cause: str,
    required_changes: list[str],
    repository_url: str | None,
) -> str:
    """
    Builder agent — revises the patch based on reviewer feedback.
    Returns the revised unified diff.
    """
    changes_text = "\n".join(f"- {c}" for c in required_changes)

    messages = [
        {
            "role": "system",
            "content": (
                "You are a data engineer revising a code fix based on review feedback. "
                "Apply all required changes. Keep the patch minimal. "
                "Return only the revised unified diff."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Root cause: {root_cause}\n"
                f"Repository: {repository_url or 'unknown'}\n\n"
                f"Original patch:\n{original_patch[:3000]}\n\n"
                f"Required changes:\n{changes_text}\n\n"
                "Return JSON:\n"
                "  revised_patch: string (unified diff)\n"
                "  changes_applied: list[string]"
            ),
        },
    ]

    response = await _gateway.chat(messages, response_format={"type": "json_object"})
    try:
        data = json.loads(response.content)
        return data.get("revised_patch", original_patch)
    except json.JSONDecodeError:
        return original_patch


async def security_agent(patch: str) -> SecurityOutput:
    """
    Security agent — independent security review focused solely on vulnerabilities.
    Does not review correctness or style.
    """
    messages = [
        {
            "role": "system",
            "content": (
                "You are a security engineer. Your only concern is security. "
                "Look for: injection vulnerabilities, hard-coded secrets, "
                "unsafe file operations, network exposure, privilege escalation, "
                "unsafe deserialization, and supply chain risks. "
                "Do not comment on code style or logic."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Patch:\n{patch[:4000]}\n\n"
                "Return JSON:\n"
                "  approved: bool\n"
                "  findings: list of { severity: critical|high|medium|low, title: string, detail: string }\n"
                "  blocked_by: list[string]  (short names of blocking issues)"
            ),
        },
    ]

    response = await _gateway.fast_chat(messages, response_format={"type": "json_object"})
    try:
        data = json.loads(response.content)
    except json.JSONDecodeError:
        data = {}

    return SecurityOutput(
        approved=bool(data.get("approved", True)),
        findings=data.get("findings", []),
        blocked_by=data.get("blocked_by", []),
    )


async def judge_agent(
    patch: str,
    root_cause: str,
    reviewer_output: ReviewerOutput,
    security_output: SecurityOutput,
    verifier_summary: str,
    revision_cycles: int,
) -> JudgeOutput:
    """
    Judge agent — makes the final approval decision before the human gate.
    Combines all agent verdicts and the deterministic verifier result.
    """
    messages = [
        {
            "role": "system",
            "content": (
                "You are the final judge on whether a code patch is ready for human review. "
                "You receive verdicts from a Reviewer, a Security agent, and a deterministic "
                "Verifier. Your decision must be coherent across all three. "
                "If the deterministic verifier blocked, you must also block."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Root cause addressed: {root_cause}\n"
                f"Revision cycles used: {revision_cycles}/{MAX_REVISION_CYCLES}\n\n"
                f"Reviewer verdict: {'APPROVED' if reviewer_output.approved else 'NEEDS CHANGES'}\n"
                f"Reviewer confidence: {reviewer_output.confidence}\n"
                f"Reviewer comments: {reviewer_output.comments}\n\n"
                f"Security verdict: {'APPROVED' if security_output.approved else 'BLOCKED'}\n"
                f"Security findings: {[f['title'] for f in security_output.findings]}\n\n"
                f"Deterministic verifier: {verifier_summary}\n\n"
                "Return JSON:\n"
                "  approved: bool\n"
                "  summary: string (one paragraph for the human reviewer)\n"
                "  required_actions: list[string]  (empty if approved)\n"
                "  confidence: float (0.0-1.0)"
            ),
        },
    ]

    response = await _gateway.chat(messages, response_format={"type": "json_object"})
    try:
        data = json.loads(response.content)
    except json.JSONDecodeError:
        data = {}

    return JudgeOutput(
        approved=bool(data.get("approved", False)),
        summary=data.get("summary", ""),
        required_actions=data.get("required_actions", []),
        confidence=float(data.get("confidence", 0.5)),
    )


# ── Orchestrator ──────────────────────────────────────────────────────────────


async def run_agent_pipeline(
    patch: str,
    root_cause: str,
    sandbox_output: str,
    repository_url: str | None,
    verifier_summary: str,
) -> AgentPipelineResult:
    """
    Drive the full multi-agent pipeline:
        Builder → Reviewer → [Builder revision loop] → Security → Judge

    Returns the final result for the runtime to act on.
    """
    current_patch = patch
    revision_cycles = 0
    all_reviewer_comments: list[str] = []
    prior_comments: list[str] = []

    # ── Builder → Reviewer loop ───────────────────────────────────────────────
    while revision_cycles < MAX_REVISION_CYCLES:
        review = await reviewer_agent(
            patch=current_patch,
            root_cause=root_cause,
            sandbox_output=sandbox_output,
            prior_comments=prior_comments,
        )
        all_reviewer_comments.extend(review.comments)

        log.info(
            "reviewer_verdict",
            cycle=revision_cycles + 1,
            approved=review.approved,
            required_changes=len(review.required_changes),
        )

        if review.approved or not review.required_changes:
            break

        # Ask the builder to revise
        prior_comments = review.required_changes
        revised = await builder_agent(
            original_patch=current_patch,
            root_cause=root_cause,
            required_changes=review.required_changes,
            repository_url=repository_url,
        )
        current_patch = revised
        revision_cycles += 1

        log.info("builder_revised", cycle=revision_cycles)

    # ── Security agent (independent — always runs) ────────────────────────────
    security = await security_agent(current_patch)

    log.info(
        "security_verdict",
        approved=security.approved,
        findings=len(security.findings),
        blocked_by=security.blocked_by,
    )

    # ── Judge ─────────────────────────────────────────────────────────────────
    final_reviewer = await reviewer_agent(
        patch=current_patch,
        root_cause=root_cause,
        sandbox_output=sandbox_output,
        prior_comments=prior_comments,
    )

    judge = await judge_agent(
        patch=current_patch,
        root_cause=root_cause,
        reviewer_output=final_reviewer,
        security_output=security,
        verifier_summary=verifier_summary,
        revision_cycles=revision_cycles,
    )

    log.info(
        "judge_verdict",
        approved=judge.approved,
        confidence=judge.confidence,
        revision_cycles=revision_cycles,
    )

    return AgentPipelineResult(
        approved=judge.approved,
        patch=current_patch,
        judge_summary=judge.summary,
        revision_cycles=revision_cycles,
        reviewer_comments=all_reviewer_comments,
        security_findings=security.findings,
        confidence=judge.confidence,
    )
