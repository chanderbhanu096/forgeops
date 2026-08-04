"""Deterministic demo data that makes the complete ForgeOps outcome visible.

Demo mode must prove more than state-machine movement. This module fills the
same MissionContext fields that real model handlers populate, so a recruiter can
see environment analysis, evidence, hypotheses, verification and a proposed fix
without needing an API key or access to an external system.
"""
from __future__ import annotations

from typing import Any

from forgeops.agent.context import Hypothesis, MissionContext, PlanStep
from forgeops.models.orm import AgentState


def demo_state_update(state: AgentState, ctx: MissionContext) -> dict[str, Any]:
    """Return realistic, JSON-serialisable updates for one demo state."""
    if state == AgentState.environment_discovery:
        return {
            "repository_url": "https://github.com/example/checkout-api",
            "environment_summary": (
                "A containerised checkout API uses FastAPI, PostgreSQL and Redis. "
                "The service is deployed through GitHub Actions to Azure Container Apps. "
                "The HTTP health endpoint is green, but checkout requests intermittently fail."
            ),
            "scratchpad": {
                **ctx.scratchpad,
                "tech_stack": [
                    "FastAPI",
                    "PostgreSQL",
                    "Redis",
                    "Docker",
                    "GitHub Actions",
                    "Azure Container Apps",
                ],
            },
        }

    if state == AgentState.plan_generation:
        return {
            "plan": [
                PlanStep(
                    step_id="1",
                    description="Compare the health-check path with the checkout request path",
                    skill_name="repository_analysis",
                ),
                PlanStep(
                    step_id="2",
                    description="Inspect application logs around failed checkout requests",
                    skill_name="log_investigation",
                ),
                PlanStep(
                    step_id="3",
                    description="Verify database-pool configuration and connection usage",
                    skill_name="sql_debugging",
                ),
                PlanStep(
                    step_id="4",
                    description="Prepare and verify the smallest safe configuration fix",
                    skill_name="deployment_validation",
                ),
            ]
        }

    if state == AgentState.evidence_collection:
        ctx.add_evidence(
            source="app/logs/checkout-api.log",
            content=(
                "ERROR checkout failed: sqlalchemy.exc.TimeoutError: QueuePool limit of "
                "size 5 overflow 0 reached; connection timed out after 30s"
            ),
            metadata={"citation": "checkout-api.log:184-190", "score": 0.98},
        )
        ctx.add_evidence(
            source="apps/api/database.py",
            content="create_async_engine(DATABASE_URL, pool_size=5, max_overflow=0)",
            metadata={"citation": "database.py:12", "score": 0.96},
        )
        ctx.add_evidence(
            source="apps/api/routes/health.py",
            content="The /health route returns process status and does not acquire a DB connection.",
            metadata={"citation": "health.py:8-14", "score": 0.91},
        )
        return {
            "relevant_files": [
                "apps/api/database.py",
                "apps/api/routes/checkout.py",
                "apps/api/routes/health.py",
            ],
            "log_excerpts": [
                "QueuePool limit of size 5 overflow 0 reached",
                "connection timed out after 30s",
            ],
            "scratchpad": {
                **ctx.scratchpad,
                "retrieval_summary": (
                    "The health route never touches PostgreSQL, while checkout requests require a "
                    "database connection. Failure logs consistently show connection-pool exhaustion."
                ),
                "retrieval_citations": [
                    "checkout-api.log:184-190 — pool timeout during checkout",
                    "database.py:12 — pool_size=5 and max_overflow=0",
                    "health.py:8-14 — health check bypasses the database",
                ],
                "retrieval_sufficient": True,
            },
        }

    if state == AgentState.hypothesis_creation:
        hypotheses = [
            Hypothesis(
                id="H1",
                description=(
                    "The PostgreSQL connection pool is too small for checkout concurrency, "
                    "causing requests to time out while the lightweight health endpoint remains green."
                ),
                confidence=0.94,
                evidence=[
                    "Checkout failures contain QueuePool timeout errors",
                    "The engine is limited to five connections with no overflow",
                    "The health endpoint does not acquire a database connection",
                ],
                rank=0,
            ),
            Hypothesis(
                id="H2",
                description="Redis latency is delaying checkout processing.",
                confidence=0.22,
                evidence=["Redis is used by the service, but no Redis timeout appears in the logs"],
                rank=1,
            ),
            Hypothesis(
                id="H3",
                description="The Azure Container App is running out of CPU.",
                confidence=0.14,
                evidence=["No CPU-throttling or restart evidence was found"],
                rank=2,
            ),
        ]
        return {"hypotheses": hypotheses, "top_hypothesis": hypotheses[0]}

    if state == AgentState.hypothesis_verification:
        return {
            "scratchpad": {
                **ctx.scratchpad,
                "verification": {
                    "confirmed": True,
                    "confidence": 0.94,
                    "findings": [
                        "Every sampled checkout failure coincides with a pool timeout",
                        "Health checks stay green because they do not test database availability",
                        "No supporting evidence was found for Redis or CPU exhaustion",
                    ],
                    "needs_more_evidence": False,
                },
            }
        }

    if state == AgentState.solution_generation:
        patch = """--- a/apps/api/database.py
+++ b/apps/api/database.py
@@ -9,7 +9,11 @@
 engine = create_async_engine(
     DATABASE_URL,
-    pool_size=5,
-    max_overflow=0,
+    pool_size=15,
+    max_overflow=10,
+    pool_timeout=10,
+    pool_pre_ping=True,
 )
"""
        return {
            "proposed_patch": patch,
            "changed_files": ["apps/api/database.py"],
            "scratchpad": {
                **ctx.scratchpad,
                "solution_explanation": (
                    "Increase pool capacity for expected checkout concurrency, fail faster when the "
                    "pool is exhausted, and validate stale connections before use."
                ),
                "recommended_regression_tests": [
                    "Run 25 concurrent checkout requests and assert no pool timeout",
                    "Simulate a stale PostgreSQL connection and verify pool_pre_ping recovery",
                    "Add a readiness check that verifies database connectivity",
                ],
            },
        }

    if state == AgentState.sandbox_execution:
        return {
            "sandbox_test_output": (
                "Applied patch in isolated sandbox.\n"
                "25 concurrent checkout requests: 25 passed.\n"
                "Database reconnection test: passed.\n"
                "Static configuration validation: passed."
            )
        }

    if state == AgentState.test_and_review:
        return {
            "test_passed": True,
            "security_findings": [
                {
                    "severity": "low",
                    "description": (
                        "Higher pool capacity increases database connection usage; verify that the "
                        "managed PostgreSQL tier supports the new maximum."
                    ),
                    "location": "apps/api/database.py",
                }
            ],
            "scratchpad": {
                **ctx.scratchpad,
                "verification": {
                    **ctx.scratchpad.get("verification", {}),
                    "passed": True,
                    "summary": "All deterministic checks and three sandbox tests passed.",
                    "findings": [
                        "Python configuration syntax is valid",
                        "No secret, destructive command or unsafe import was introduced",
                        "Concurrent checkout test passed 25/25 requests",
                    ],
                },
                "agent_pipeline": {
                    "revision_cycles": 0,
                    "judge_summary": (
                        "The evidence supports connection-pool exhaustion as the root cause. "
                        "The proposed one-file configuration change is minimal, reversible and "
                        "validated under concurrent load."
                    ),
                    "confidence": 0.94,
                    "reviewer_comments": [
                        "Add database connectivity to readiness checks",
                        "Monitor active connections and pool wait time after deployment",
                        "Confirm the PostgreSQL service connection limit before production rollout",
                    ],
                },
            },
        }

    if state == AgentState.execution:
        return {
            "pull_request_url": "https://github.com/example/checkout-api/pull/42",
            "pull_request_number": 42,
        }

    if state == AgentState.post_action_monitoring:
        return {
            "scratchpad": {
                **ctx.scratchpad,
                "monitoring": {
                    "status": "healthy",
                    "observations": [
                        "Checkout success rate: 100% in the simulated post-deployment window",
                        "Pool wait timeout count: 0",
                        "p95 checkout latency improved from 31.2s to 420ms",
                    ],
                    "rollback_recommended": False,
                },
            }
        }

    return {}
