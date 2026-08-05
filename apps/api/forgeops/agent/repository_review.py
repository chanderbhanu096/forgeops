"""Repository-specific mission handlers with deterministic GitHub retrieval."""
from __future__ import annotations

import json
import re
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from forgeops.agent.context import MissionContext, PlanStep
from forgeops.agent.gateway import ModelGateway
from forgeops.agent.handlers import (
    handle_environment_discovery as handle_legacy_environment_discovery,
)
from forgeops.agent.handlers import handle_evidence_collection as handle_legacy_evidence_collection
from forgeops.agent.handlers import handle_plan_generation as handle_legacy_plan_generation
from forgeops.agent.evidence_policy import is_repository_analysis
from forgeops.integrations.github_repository import (
    GitHubRepositoryClient,
    RepositorySnapshot,
    normalise_github_repository_url,
)

log = structlog.get_logger(__name__)
_gateway = ModelGateway()

_GITHUB_URL = re.compile(r"https?://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(?:\.git)?")
_READ_ONLY_TERMS = (
    "overview",
    "review",
    "audit",
    "analy",
    "investigate",
    "explain",
    "understand",
    "architecture",
)
_MUTATION_TERMS = (
    "fix ",
    "implement",
    "change ",
    "patch ",
    "modify",
    "create a pull request",
    "open a pull request",
)


def _extract_repository_url(ctx: MissionContext) -> str | None:
    text = f"{ctx.title}\n{ctx.description}"
    match = _GITHUB_URL.search(text)
    if not match:
        return None
    return normalise_github_repository_url(match.group(0))


def _is_read_only_overview(ctx: MissionContext) -> bool:
    text = f"{ctx.title}\n{ctx.description}".lower()
    return any(term in text for term in _READ_ONLY_TERMS) and not any(
        term in text for term in _MUTATION_TERMS
    )


async def handle_environment_discovery(
    ctx: MissionContext,
    db: AsyncSession,
) -> dict[str, Any]:
    """Resolve repository identity without asking the model to invent tool calls."""
    repository_url = _extract_repository_url(ctx)
    if not repository_url:
        return await handle_legacy_environment_discovery(ctx, db)

    mode = "repository_overview" if _is_read_only_overview(ctx) else "repository_change"
    return {
        "repository_url": repository_url,
        "environment_summary": (
            f"Repository target identified: {repository_url}. "
            "ForgeOps will inspect the default branch and pin all findings to a commit "
            "before generating conclusions."
        ),
        "scratchpad": {
            **ctx.scratchpad,
            "mission_mode": mode,
            "report_type": "repository_review",
        },
    }


async def handle_plan_generation(
    ctx: MissionContext,
    db: AsyncSession,
) -> dict[str, Any]:
    """Use a deterministic read-only plan for repository overview missions."""
    if ctx.scratchpad.get("mission_mode") != "repository_overview":
        return await handle_legacy_plan_generation(ctx, db)

    return {
        "plan": [
            PlanStep(
                step_id="1",
                description="Resolve repository, default branch and immutable commit SHA",
                skill_name="repository_analysis",
            ),
            PlanStep(
                step_id="2",
                description="Inspect documentation, manifests, workflows and core source files",
                skill_name="repository_analysis",
            ),
            PlanStep(
                step_id="3",
                description="Build an evidence-backed architecture and engineering overview",
                skill_name="data_lineage_analysis",
            ),
            PlanStep(
                step_id="4",
                description="Rank strengths, risks and recommended next steps with citations",
                skill_name="deployment_validation",
            ),
        ]
    }


async def handle_evidence_collection(
    ctx: MissionContext,
    db: AsyncSession,
) -> dict[str, Any]:
    """Inspect a real GitHub repository and generate a source-grounded overview."""
    if not is_repository_analysis(ctx) or not ctx.repository_url:
        return await handle_legacy_evidence_collection(ctx, db)

    client = GitHubRepositoryClient()
    snapshot = await client.inspect(
        ctx.repository_url,
        ctx.description,
        max_files=24,
    )
    for file in snapshot.files:
        ctx.add_evidence(
            source=file.path,
            content=file.content,
            metadata={
                "citation": file.citation,
                "repository": snapshot.identity.url,
                "commit_sha": snapshot.identity.commit_sha,
                "size": file.size,
            },
        )

    report = await _generate_repository_report(ctx, snapshot)
    identity = snapshot.identity
    citations = [file.citation for file in snapshot.files]
    environment_summary = (
        f"Inspected {identity.owner}/{identity.name} on {identity.default_branch} at commit "
        f"{identity.commit_sha[:12]}. Reviewed {len(snapshot.files)} selected text files from "
        f"{snapshot.tree_file_count} repository files. Detected stack: "
        f"{', '.join(snapshot.detected_stack) if snapshot.detected_stack else 'not confirmed'}."
    )
    return {
        "repository_url": identity.url,
        "environment_summary": environment_summary,
        "relevant_files": [file.path for file in snapshot.files],
        "scratchpad": {
            **ctx.scratchpad,
            "repository_identity": {
                "owner": identity.owner,
                "name": identity.name,
                "url": identity.url,
                "default_branch": identity.default_branch,
                "commit_sha": identity.commit_sha,
                "files_inspected": len(snapshot.files),
                "repository_file_count": snapshot.tree_file_count,
                "tree_truncated": snapshot.tree_truncated,
            },
            "tech_stack": snapshot.detected_stack,
            "retrieval_summary": report.get("overview", environment_summary),
            "retrieval_citations": citations,
            "retrieval_sufficient": True,
            "repository_report": report,
        },
    }


async def _generate_repository_report(
    ctx: MissionContext,
    snapshot: RepositorySnapshot,
) -> dict[str, Any]:
    evidence_blocks: list[str] = []
    total = 0
    for file in snapshot.files:
        block = f"SOURCE: {file.citation}\nPATH: {file.path}\n{file.content[:12_000]}"
        if total + len(block) > 70_000:
            break
        evidence_blocks.append(block)
        total += len(block)

    messages = [
        {
            "role": "system",
            "content": (
                "You are a principal software architect performing a read-only repository "
                "review. Use only the supplied repository evidence. Never call tools. Never "
                "invent files, frameworks, test results, runtime health, performance numbers, "
                "or security findings. Every nontrivial claim must cite at least one supplied "
                "SOURCE exactly. Return one valid JSON object and no markdown."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Mission: {ctx.description}\n"
                f"Repository: {snapshot.identity.url}\n"
                f"Branch: {snapshot.identity.default_branch}\n"
                f"Commit: {snapshot.identity.commit_sha}\n"
                f"Detected stack hints: {snapshot.detected_stack}\n\n"
                "Return JSON with this schema:\n"
                "{\n"
                '  "overview": "plain-English project summary",\n'
                '  "architecture": ["component or data-flow statement with SOURCE citation"],\n'
                '  "strengths": [{"title":"", "detail":"", "evidence":["SOURCE"]}],\n'
                '  "risks": [{"title":"", "severity":"low|medium|high", '
                '"detail":"", "evidence":["SOURCE"]}],\n'
                '  "recommendations": [{"priority":1, "title":"", "detail":"", '
                '"evidence":["SOURCE"]}],\n'
                '  "confirmed_facts": ["fact with SOURCE citation"],\n'
                '  "assumptions": ["clearly labelled unverified assumption"],\n'
                '  "confidence": 0.0\n'
                "}\n\n"
                "Repository evidence:\n"
                + "\n\n---\n\n".join(evidence_blocks)
            ),
        },
    ]

    try:
        response = await _gateway.chat(
            messages,
            response_format={"type": "json_object"},
            temperature=0.1,
            max_tokens=5000,
            _handler="repository_overview",
        )
        ctx.add_model_cost(response.cost_usd)
        data = json.loads(response.content)
        if not isinstance(data, dict) or not str(data.get("overview", "")).strip():
            raise ValueError("Repository overview model response was incomplete")
        data["confidence"] = max(0.0, min(1.0, float(data.get("confidence", 0.0))))
        return data
    except Exception as exc:
        log.warning("repository_report_model_fallback", error=str(exc))
        return _fallback_repository_report(snapshot)


def _fallback_repository_report(snapshot: RepositorySnapshot) -> dict[str, Any]:
    identity = snapshot.identity
    paths = [file.path for file in snapshot.files]
    readme = next((file for file in snapshot.files if file.path.lower() == "readme.md"), None)
    workflows = [path for path in paths if path.startswith(".github/workflows/")]
    manifests = [
        path
        for path in paths
        if path.lower().endswith(("pyproject.toml", "package.json", "requirements.txt"))
    ]
    overview = (
        f"{identity.owner}/{identity.name} is a repository on the {identity.default_branch} "
        f"branch. ForgeOps inspected {len(snapshot.files)} selected files at commit "
        f"{identity.commit_sha[:12]}. Confirmed technologies include "
        f"{', '.join(snapshot.detected_stack) if snapshot.detected_stack else 'no stack yet'}."
    )
    architecture = [
        f"Repository documentation entry point: {readme.citation}" if readme else (
            "No README was present in the selected evidence; project intent requires manual "
            "confirmation."
        ),
        f"Dependency manifests inspected: {', '.join(manifests)}" if manifests else (
            "No dependency manifest was present in the selected evidence."
        ),
    ]
    strengths: list[dict[str, Any]] = []
    if readme:
        strengths.append(
            {
                "title": "Project documentation is present",
                "detail": "A README is available as an onboarding and intent reference.",
                "evidence": [readme.citation],
            }
        )
    if workflows:
        strengths.append(
            {
                "title": "Automated workflows are present",
                "detail": "GitHub Actions workflow definitions were found and inspected.",
                "evidence": workflows,
            }
        )
    risks = [
        {
            "title": "Semantic review fallback used",
            "severity": "medium",
            "detail": (
                "The configured model could not produce a valid evidence-grounded JSON report. "
                "The repository identity and file evidence are valid, but deeper conclusions "
                "require another model run or human review."
            ),
            "evidence": [file.citation for file in snapshot.files[:3]],
        }
    ]
    return {
        "overview": overview,
        "architecture": architecture,
        "strengths": strengths,
        "risks": risks,
        "recommendations": [
            {
                "priority": 1,
                "title": "Review the inspected evidence",
                "detail": "Use the cited files to complete a human architecture and risk review.",
                "evidence": [file.citation for file in snapshot.files[:5]],
            }
        ],
        "confirmed_facts": [
            f"Default branch is {identity.default_branch} at {identity.commit_sha}.",
            f"ForgeOps inspected {len(snapshot.files)} readable files.",
        ],
        "assumptions": [],
        "confidence": 0.65,
    }
