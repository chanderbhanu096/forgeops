"""
State handlers — one coroutine per agent state.

Each handler receives the current MissionContext and the DB session,
does its work (calls the model gateway, invokes MCP tools, etc.) and
returns a dict of context updates. The runtime merges the dict back
into the context and persists a checkpoint.

Handlers must:
    - Be idempotent (safe to re-run after a crash).
    - Never modify the database directly — updates go through the context.
    - Raise exceptions on unrecoverable errors.
"""
from __future__ import annotations

import json
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from forgeops.agent.context import Hypothesis, MissionContext, PlanStep
from forgeops.agent.gateway import ModelGateway
from forgeops.agent.multi_agent import run_agent_pipeline
from forgeops.retrieval.orchestrator import RetrievalOrchestrator
from forgeops.verification.pipeline import get_pipeline

log = structlog.get_logger(__name__)
_gateway = ModelGateway()


# ── 1. Environment discovery ──────────────────────────────────────────────────


async def handle_environment_discovery(
    ctx: MissionContext, db: AsyncSession
) -> dict[str, Any]:
    """
    Understand the engineering environment from the mission description.
    Asks the model to extract: repository URL, technology stack, key services.
    """
    messages = [
        {
            "role": "system",
            "content": (
                "You are an expert data and cloud engineer. "
                "Extract structured environment information from the mission description."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Mission: {ctx.description}\n\n"
                "Return a JSON object with:\n"
                "  repository_url: string | null\n"
                "  tech_stack: list[string]\n"
                "  key_services: list[string]\n"
                "  environment_summary: string (2-3 sentences)\n"
                "Return only the JSON object, no markdown."
            ),
        },
    ]

    response = await _gateway.chat(messages, response_format={"type": "json_object"})
    ctx.add_model_cost(response.cost_usd)

    try:
        data = json.loads(response.content)
    except json.JSONDecodeError:
        log.warning("environment_discovery_json_parse_failed", raw=response.content[:200])
        data = {}

    log.info(
        "environment_discovered",
        repository_url=data.get("repository_url"),
        tech_stack=data.get("tech_stack", []),
    )

    return {
        "repository_url": data.get("repository_url"),
        "environment_summary": data.get("environment_summary", ""),
        "scratchpad": {**ctx.scratchpad, "tech_stack": data.get("tech_stack", [])},
    }


# ── 2. Plan generation ────────────────────────────────────────────────────────


async def handle_plan_generation(
    ctx: MissionContext, db: AsyncSession
) -> dict[str, Any]:
    """
    Produce a concrete, ordered plan for solving the mission.
    Each step maps to a skill name where possible.
    """
    messages = [
        {
            "role": "system",
            "content": (
                "You are an autonomous AI data and cloud engineer. "
                "Create a step-by-step execution plan for the given mission. "
                "Be specific. Each step must have a clear deliverable."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Mission: {ctx.description}\n"
                f"Environment: {ctx.environment_summary}\n\n"
                "Return a JSON object with:\n"
                '  plan: list of { step_id, description, skill_name, estimated_cost_usd }\n'
                "Available skills: repository_analysis, log_investigation, sql_debugging, "
                "schema_comparison, data_lineage_analysis, dbt_model_repair, "
                "pull_request_creation, deployment_validation\n"
                "Return only the JSON object."
            ),
        },
    ]

    response = await _gateway.chat(messages, response_format={"type": "json_object"})
    ctx.add_model_cost(response.cost_usd)

    try:
        data = json.loads(response.content)
        steps = data.get("plan", [])
    except json.JSONDecodeError:
        steps = []

    plan = [
        PlanStep(
            step_id=s.get("step_id", str(i)),
            description=s.get("description", ""),
            skill_name=s.get("skill_name"),
            estimated_cost_usd=float(s.get("estimated_cost_usd", 0.0)),
        )
        for i, s in enumerate(steps)
    ]

    log.info("plan_generated", steps=len(plan))
    return {"plan": plan}


# ── 3. Evidence collection ────────────────────────────────────────────────────


async def handle_evidence_collection(
    ctx: MissionContext, db: AsyncSession
) -> dict[str, Any]:
    """
    Gather evidence using the agentic retrieval pipeline.

    The RetrievalOrchestrator decomposes the mission question, routes each
    sub-query to the appropriate source, retrieves and reranks results,
    and verifies whether the evidence is sufficient.

    Evidence is stored in ctx.raw_evidence for downstream handlers.
    """
    retriever = RetrievalOrchestrator(db)

    # Build the core question from the mission description + plan
    plan_steps = " → ".join(s.description for s in ctx.plan[:5])
    question = (
        f"What is the root cause of: {ctx.description}\n"
        f"Investigation plan: {plan_steps}"
    )

    result = await retriever.retrieve(
        question=question,
        context=ctx.environment_summary,
        max_sub_queries=3,
    )

    # Load retrieved documents as evidence
    for doc in result.documents:
        ctx.add_evidence(
            source=doc.source,
            content=doc.content,
            metadata={"score": doc.score, "citation": doc.citation},
        )

    log.info(
        "evidence_collected",
        documents=len(result.documents),
        sufficient=result.sufficient,
        citations=len(result.citations),
    )

    return {
        "scratchpad": {
            **ctx.scratchpad,
            "retrieval_summary": result.summary,
            "retrieval_citations": result.citations,
            "retrieval_sufficient": result.sufficient,
        }
    }


# ── 4. Hypothesis creation ────────────────────────────────────────────────────


async def handle_hypothesis_creation(
    ctx: MissionContext, db: AsyncSession
) -> dict[str, Any]:
    """
    Generate ranked hypotheses for the root cause.
    """
    evidence_summary = "\n".join(
        f"- [{e['source']}] {e['content'][:200]}" for e in ctx.raw_evidence
    )

    messages = [
        {
            "role": "system",
            "content": (
                "You are a principal data engineer performing root cause analysis. "
                "Generate a ranked list of hypotheses ordered by confidence."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Mission: {ctx.description}\n"
                f"Evidence collected:\n{evidence_summary or '(no evidence yet)'}\n\n"
                "Generate hypotheses as JSON:\n"
                "  hypotheses: list of { id, description, confidence, evidence }\n"
                "confidence is 0.0-1.0. Rank from highest to lowest.\n"
                "Return only the JSON object."
            ),
        },
    ]

    response = await _gateway.chat(messages, response_format={"type": "json_object"})
    ctx.add_model_cost(response.cost_usd)

    try:
        data = json.loads(response.content)
        raw_hypotheses = data.get("hypotheses", [])
    except json.JSONDecodeError:
        raw_hypotheses = []

    hypotheses = [
        Hypothesis(
            id=h.get("id", str(i)),
            description=h.get("description", ""),
            confidence=float(h.get("confidence", 0.5)),
            evidence=h.get("evidence", []),
            rank=i,
        )
        for i, h in enumerate(raw_hypotheses)
    ]

    top = hypotheses[0] if hypotheses else None
    log.info(
        "hypotheses_generated", count=len(hypotheses), top_confidence=top.confidence if top else 0
    )
    return {"hypotheses": hypotheses, "top_hypothesis": top}


# ── 5. Hypothesis verification ────────────────────────────────────────────────


async def handle_hypothesis_verification(
    ctx: MissionContext, db: AsyncSession
) -> dict[str, Any]:
    """
    Test the top hypothesis against available evidence.
    Returns whether to proceed to solution generation or loop back.
    """
    if not ctx.top_hypothesis:
        return {}

    messages = [
        {
            "role": "system",
            "content": (
                "You are verifying a root cause hypothesis for a data engineering incident. "
                "Be rigorous. Look for contradictions in the evidence."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Hypothesis: {ctx.top_hypothesis.description}\n"
                f"Confidence: {ctx.top_hypothesis.confidence}\n"
                f"Supporting evidence: {ctx.top_hypothesis.evidence}\n\n"
                "Evaluate as JSON:\n"
                "  confirmed: bool\n"
                "  confidence: float (0.0-1.0)\n"
                "  findings: list[string]\n"
                "  needs_more_evidence: bool\n"
                "Return only the JSON object."
            ),
        },
    ]

    response = await _gateway.chat(messages, response_format={"type": "json_object"})
    ctx.add_model_cost(response.cost_usd)

    try:
        data = json.loads(response.content)
    except json.JSONDecodeError:
        data = {"confirmed": False, "confidence": 0.3, "findings": [], "needs_more_evidence": True}

    log.info(
        "hypothesis_verified",
        confirmed=data.get("confirmed"),
        confidence=data.get("confidence"),
    )

    # Update the top hypothesis confidence
    if ctx.top_hypothesis:
        ctx.top_hypothesis.confidence = float(data.get("confidence", ctx.top_hypothesis.confidence))

    return {"scratchpad": {**ctx.scratchpad, "verification": data}}


# ── 6. Solution generation ────────────────────────────────────────────────────


async def handle_solution_generation(
    ctx: MissionContext, db: AsyncSession
) -> dict[str, Any]:
    """
    Generate a concrete code fix for the confirmed root cause.
    """
    if not ctx.top_hypothesis:
        raise RuntimeError("Cannot generate solution: no confirmed hypothesis")

    messages = [
        {
            "role": "system",
            "content": (
                "You are an autonomous data engineer. Generate a minimal, safe code fix. "
                "Return only a unified diff. Do not add unnecessary changes."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Root cause: {ctx.top_hypothesis.description}\n"
                f"Repository: {ctx.repository_url or 'unknown'}\n"
                f"Environment: {ctx.environment_summary}\n\n"
                "Produce:\n"
                "  proposed_patch: string (unified diff format)\n"
                "  changed_files: list[string]\n"
                "  explanation: string\n"
                "Return only the JSON object."
            ),
        },
    ]

    response = await _gateway.chat(messages, response_format={"type": "json_object"})
    ctx.add_model_cost(response.cost_usd)

    try:
        data = json.loads(response.content)
    except json.JSONDecodeError:
        data = {}

    log.info("solution_generated", changed_files=data.get("changed_files", []))
    return {
        "proposed_patch": data.get("proposed_patch"),
        "changed_files": data.get("changed_files", []),
    }


# ── 7. Sandbox execution ──────────────────────────────────────────────────────


async def handle_sandbox_execution(
    ctx: MissionContext, db: AsyncSession
) -> dict[str, Any]:
    """
    Apply the patch in an isolated sandbox environment.
    In a full implementation this calls the sandbox service via HTTP.
    """
    if not ctx.proposed_patch:
        raise RuntimeError("No patch to execute in sandbox")

    log.info("sandbox_execution_started", changed_files=ctx.changed_files)

    # Placeholder: in v2 this calls services/sandbox via HTTP
    sandbox_output = (
        f"[SANDBOX] Applied patch to {len(ctx.changed_files)} file(s).\n"
        f"Patch size: {len(ctx.proposed_patch)} chars.\n"
        "[SANDBOX] Environment ready for testing."
    )

    return {"sandbox_test_output": sandbox_output}


# ── 8. Test and review ────────────────────────────────────────────────────────


async def handle_test_and_review(
    ctx: MissionContext, db: AsyncSession
) -> dict[str, Any]:
    """
    Run the full verification pipeline then the model reviewer.

    Sequence:
        1. Deterministic verifiers (syntax, dangerous patterns, imports, size)
        2. Model reviewer (correctness, missing tests, review comments)
        3. Security agent via model (injection, secrets, permissions)
        4. Judge: combine deterministic + model verdicts

    The verifier pipeline is the hard gate — critical findings block approval
    regardless of what the model reviewer says.
    """
    if not ctx.proposed_patch:
        raise RuntimeError("No patch to review")

    # ── Step 1: Deterministic verifier pipeline ────────────────────────────
    pipeline = get_pipeline()
    verification_result = await pipeline.verify_patch(
        ctx.proposed_patch,
        changed_files=ctx.changed_files,
    )

    verifier_findings = [
        {"severity": f.severity, "description": f"{f.title} — {f.detail}", "location": f.location}
        for f in verification_result.all_findings
    ]

    log.info(
        "deterministic_verification_complete",
        passed=verification_result.passed,
        critical=verification_result.critical_count,
        high=verification_result.high_count,
        total_findings=len(verification_result.all_findings),
    )

    # If critical issues found, skip model review and fail immediately
    if verification_result.critical_count > 0:
        log.warning(
            "test_and_review_failed_critical",
            critical_count=verification_result.critical_count,
        )
        return {
            "test_passed": False,
            "security_findings": verifier_findings,
            "scratchpad": {
                **ctx.scratchpad,
                "verification": verification_result.to_dict(),
                "review": {"blocked_by": "deterministic_verifier"},
            },
        }

    # ── Step 2–4: Multi-agent pipeline (Builder → Reviewer → Security → Judge)
    root_cause = ctx.top_hypothesis.description if ctx.top_hypothesis else "unknown"
    agent_result = await run_agent_pipeline(
        patch=ctx.proposed_patch,
        root_cause=root_cause,
        sandbox_output=ctx.sandbox_test_output or "",
        repository_url=ctx.repository_url,
        verifier_summary=verification_result.summary,
    )

    # Merge verifier findings with agent security findings
    all_security_findings = verifier_findings + agent_result.security_findings

    overall_passed = verification_result.passed and agent_result.approved

    log.info(
        "test_and_review_complete",
        test_passed=overall_passed,
        verifier_passed=verification_result.passed,
        agent_approved=agent_result.approved,
        revision_cycles=agent_result.revision_cycles,
        confidence=agent_result.confidence,
        total_findings=len(all_security_findings),
    )

    return {
        "test_passed": overall_passed,
        # Use the potentially revised patch from the builder
        "proposed_patch": agent_result.patch,
        "security_findings": all_security_findings,
        "scratchpad": {
            **ctx.scratchpad,
            "verification": verification_result.to_dict(),
            "agent_pipeline": {
                "revision_cycles": agent_result.revision_cycles,
                "judge_summary": agent_result.judge_summary,
                "confidence": agent_result.confidence,
                "reviewer_comments": agent_result.reviewer_comments,
            },
        },
    }


# ── 9. Execution ──────────────────────────────────────────────────────────────


async def handle_execution(
    ctx: MissionContext, db: AsyncSession
) -> dict[str, Any]:
    """
    Execute approved changes. In v2: apply patch via GitHub MCP, trigger CI.
    Here we record the intent and simulate PR creation.
    """
    log.info("execution_started", patch_size=len(ctx.proposed_patch or ""))

    # Placeholder: v2 calls mcp-github create_pull_request
    pr_url = "https://github.com/example/repo/pull/42"
    log.info("pull_request_created", url=pr_url)

    return {
        "pull_request_url": pr_url,
        "pull_request_number": 42,
    }


# ── 10. Post-action monitoring ────────────────────────────────────────────────


async def handle_post_action_monitoring(
    ctx: MissionContext, db: AsyncSession
) -> dict[str, Any]:
    """
    Monitor the pipeline after the fix is applied, then write operational memory.

    1. Ask the model to produce a monitoring report.
    2. Write episodic memory for the completed mission.
    3. If the fix succeeded, record the successful strategy as procedural memory.
    """
    from forgeops.memory.store import MemoryStore, MissionMemoryWriter

    log.info("post_action_monitoring_started", pr_url=ctx.pull_request_url)

    messages = [
        {
            "role": "system",
            "content": "You are monitoring a data pipeline after a fix was applied.",
        },
        {
            "role": "user",
            "content": (
                f"Pull request: {ctx.pull_request_url}\n"
                f"Original root cause: "
                f"{ctx.top_hypothesis.description if ctx.top_hypothesis else 'unknown'}\n"
                f"Fix applied to: {ctx.changed_files}\n\n"
                "Produce a monitoring report as JSON:\n"
                "  status: 'healthy' | 'degraded' | 'failed'\n"
                "  observations: list[string]\n"
                "  rollback_recommended: bool\n"
                "  strategy_learned: string | null  "
                "(one-sentence reusable strategy for future missions)\n"
                "Return only the JSON object."
            ),
        },
    ]

    response = await _gateway.chat(messages, response_format={"type": "json_object"})
    ctx.add_model_cost(response.cost_usd)

    try:
        data = json.loads(response.content)
    except json.JSONDecodeError:
        data = {"status": "healthy", "observations": [], "rollback_recommended": False}

    status = data.get("status", "healthy")
    log.info("monitoring_complete", status=status)

    if data.get("rollback_recommended"):
        log.warning("rollback_recommended_by_monitoring")

    # ── Write operational memory ──────────────────────────────────────────────
    root_cause = ctx.top_hypothesis.description if ctx.top_hypothesis else ""
    outcome = "success" if status == "healthy" else "failure"
    solution_summary = ctx.scratchpad.get("agent_pipeline", {}).get("judge_summary", "")

    store = MemoryStore(db)
    writer = MissionMemoryWriter(store)

    await writer.write_mission_summary(
        mission_id=ctx.mission_id,
        root_cause=root_cause,
        solution_summary=solution_summary,
        outcome=outcome,
        changed_files=ctx.changed_files,
        pr_url=ctx.pull_request_url,
    )

    # If mission succeeded and a reusable strategy was identified, learn it
    strategy = data.get("strategy_learned")
    if strategy and status == "healthy":
        tech_tags = ctx.scratchpad.get("tech_stack", [])
        await writer.learn_procedural(
            mission_id=ctx.mission_id,
            strategy=strategy,
            context_tags=tech_tags[:5],
        )

    await db.commit()

    return {
        "scratchpad": {
            **ctx.scratchpad,
            "monitoring": data,
        }
    }
