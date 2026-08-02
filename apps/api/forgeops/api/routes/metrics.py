"""
Prometheus metrics endpoint.

Exposes:
  - forgeops_missions_total{status}         — lifetime mission count by status
  - forgeops_missions_active                — missions in a non-terminal status
  - forgeops_model_cost_usd_total           — cumulative LLM spend across all missions
  - forgeops_tool_calls_total{server,tool}  — MCP tool invocations
  - forgeops_verifier_runs_total{pipeline,passed} — verification pipeline executions
  - forgeops_approvals_pending              — approvals awaiting human decision

All counters are computed by querying the existing Postgres/SQLite ORM tables so
there is no separate push-gateway or in-process counter state to keep in sync.
The endpoint is cheap: each metric issues at most one COUNT query.
"""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse
from sqlalchemy import func, select

from forgeops.db import get_session_factory
from forgeops.models.orm import (
    Approval,
    ApprovalDecision,
    Mission,
    MissionStatus,
    ToolCall,
    ToolCallStatus,
)

router = APIRouter()


def _gauge(name: str, value: float, labels: dict[str, str] | None = None) -> str:
    """Format a single Prometheus gauge line."""
    if labels:
        label_str = ",".join(f'{k}="{v}"' for k, v in labels.items())
        return f"{name}{{{label_str}}} {value}"
    return f"{name} {value}"


@router.get(
    "/metrics",
    response_class=PlainTextResponse,
    include_in_schema=False,
    summary="Prometheus metrics",
)
async def prometheus_metrics() -> str:
    """
    Returns metrics in Prometheus text exposition format (0.0.4).

    This endpoint is intentionally unauthenticated so that a Prometheus
    scraper can reach it without credentials.  It must NOT be exposed to
    the public internet — restrict access at the load-balancer / security-
    group level.
    """
    lines: list[str] = []

    async with get_session_factory()() as session:
        # ── missions_total by status ──────────────────────────────────────────
        lines.append("# HELP forgeops_missions_total Lifetime mission count by status")
        lines.append("# TYPE forgeops_missions_total gauge")

        rows = await session.execute(
            select(Mission.status, func.count(Mission.id).label("cnt"))
            .group_by(Mission.status)
        )
        status_counts: dict[str, int] = {}
        for row in rows:
            status_counts[str(row.status)] = int(row.cnt)
            lines.append(_gauge("forgeops_missions_total", row.cnt, {"status": str(row.status)}))

        # ── missions_active ───────────────────────────────────────────────────
        _terminal = {MissionStatus.completed, MissionStatus.failed, MissionStatus.rolled_back}
        active_count = sum(v for k, v in status_counts.items() if k not in _terminal)
        lines.append("# HELP forgeops_missions_active Missions in a non-terminal status")
        lines.append("# TYPE forgeops_missions_active gauge")
        lines.append(_gauge("forgeops_missions_active", active_count))

        # ── model_cost_usd_total ──────────────────────────────────────────────
        lines.append("# HELP forgeops_model_cost_usd_total Cumulative LLM cost in USD")
        lines.append("# TYPE forgeops_model_cost_usd_total counter")

        cost_row = await session.execute(
            select(func.coalesce(func.sum(Mission.cost_usd_used), 0.0))
        )
        total_cost: float = float(cost_row.scalar_one())
        lines.append(_gauge("forgeops_model_cost_usd_total", total_cost))

        # ── tool_calls_total by server + tool ─────────────────────────────────
        lines.append("# HELP forgeops_tool_calls_total MCP tool invocations")
        lines.append("# TYPE forgeops_tool_calls_total counter")

        tool_rows = await session.execute(
            select(
                ToolCall.server,
                ToolCall.tool_name,
                func.count(ToolCall.id).label("cnt"),
            ).group_by(ToolCall.server, ToolCall.tool_name)
        )
        for row in tool_rows:
            lines.append(
                _gauge(
                    "forgeops_tool_calls_total",
                    int(row.cnt),
                    {"server": str(row.server), "tool": str(row.tool_name)},
                )
            )

        # ── verifier_runs_total by pipeline + passed ──────────────────────────
        # Verification runs are recorded in ToolCall rows where server == "verifier"
        lines.append("# HELP forgeops_verifier_runs_total Verification pipeline executions")
        lines.append("# TYPE forgeops_verifier_runs_total counter")

        verifier_rows = await session.execute(
            select(
                ToolCall.tool_name,
                ToolCall.status,
                func.count(ToolCall.id).label("cnt"),
            )
            .where(ToolCall.server == "verifier")
            .group_by(ToolCall.tool_name, ToolCall.status)
        )
        for row in verifier_rows:
            passed = row.status == ToolCallStatus.succeeded
            lines.append(
                _gauge(
                    "forgeops_verifier_runs_total",
                    int(row.cnt),
                    {
                        "pipeline": str(row.tool_name),
                        "passed": "true" if passed else "false",
                    },
                )
            )

        # ── approvals_pending ─────────────────────────────────────────────────
        lines.append("# HELP forgeops_approvals_pending Approvals awaiting human decision")
        lines.append("# TYPE forgeops_approvals_pending gauge")

        pending_row = await session.execute(
            select(func.count(Approval.id)).where(
                Approval.decision == ApprovalDecision.pending
            )
        )
        pending_count = int(pending_row.scalar_one())
        lines.append(_gauge("forgeops_approvals_pending", pending_count))

    return "\n".join(lines) + "\n"
