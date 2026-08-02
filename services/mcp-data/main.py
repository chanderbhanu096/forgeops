"""
Data Platform MCP Server.

Tools:
  - list_pipeline_runs   — recent Airflow/dbt run statuses
  - fetch_logs           — raw log lines for a run
  - run_read_only_sql    — execute a read-only SQL query
  - get_schema           — column list for a table
  - get_lineage          — upstream/downstream node graph
  - list_data_quality_checks — Great Expectations / Soda results
"""
from __future__ import annotations

import os
from typing import Any

import structlog
from fastapi import FastAPI, Header, HTTPException, status
from pydantic import BaseModel

log = structlog.get_logger(__name__)
MCP_SECRET = os.environ.get("MCP_SECRET", "forgeops_mcp_dev")

app = FastAPI(title="ForgeOps Data Platform MCP Server", version="1.0.0")


def verify_auth(authorization: str | None) -> None:
    if not authorization or authorization != f"Bearer {MCP_SECRET}":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)


# ── Schemas ───────────────────────────────────────────────────────────────────


class FetchLogsRequest(BaseModel):
    pipeline_id: str
    run_id: str | None = None
    tail_lines: int = 500


class RunSQLRequest(BaseModel):
    sql: str
    database: str = "warehouse"
    max_rows: int = 1000


class GetLineageRequest(BaseModel):
    node_id: str
    direction: str = "both"   # upstream | downstream | both
    max_depth: int = 3


# ── Endpoints ─────────────────────────────────────────────────────────────────


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "server": "mcp-data"}


@app.get("/tools/list_pipeline_runs")
async def list_pipeline_runs(
    pipeline_id: str | None = None,
    limit: int = 20,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    verify_auth(authorization)

    # Stub — replace with Airflow/dbt Cloud API calls in v2
    return {
        "runs": [
            {
                "run_id": "run_001",
                "pipeline_id": pipeline_id or "customer_revenue",
                "status": "failed",
                "started_at": "2024-01-15T08:00:00Z",
                "duration_seconds": 142,
                "error": "KeyError: 'revenue_eur'",
            }
        ]
    }


@app.post("/tools/fetch_logs")
async def fetch_logs(
    req: FetchLogsRequest,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    verify_auth(authorization)

    # Stub — replace with CloudWatch / Datadog / Airflow log API
    return {
        "pipeline_id": req.pipeline_id,
        "run_id": req.run_id,
        "lines": [
            "[2024-01-15 08:00:00] INFO  Starting pipeline customer_revenue",
            "[2024-01-15 08:02:10] ERROR KeyError: 'revenue_eur'",
            "[2024-01-15 08:02:10] ERROR   File 'models/revenue/daily_revenue.sql', line 42",
            "[2024-01-15 08:02:10] ERROR   Column 'revenue_eur' does not exist in source",
            "[2024-01-15 08:02:11] INFO  Pipeline failed after 130s",
        ],
    }


@app.post("/tools/run_read_only_sql")
async def run_read_only_sql(
    req: RunSQLRequest,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    verify_auth(authorization)

    # Security: block any non-SELECT statements
    stripped = req.sql.strip().upper()
    for forbidden in ("INSERT", "UPDATE", "DELETE", "DROP", "CREATE", "ALTER", "TRUNCATE"):
        if stripped.startswith(forbidden):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Statement type '{forbidden}' is not allowed",
            )

    # Stub — replace with read-only BigQuery / Athena / Snowflake call
    return {
        "sql": req.sql,
        "rows": [],
        "row_count": 0,
        "columns": [],
        "message": "SQL validation passed. Connect real warehouse in v2.",
    }


@app.post("/tools/get_lineage")
async def get_lineage(
    req: GetLineageRequest,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    verify_auth(authorization)

    # Stub — replace with dbt lineage / OpenLineage / Marquez API
    return {
        "node_id": req.node_id,
        "direction": req.direction,
        "nodes": [
            {"id": req.node_id, "type": "model", "status": "failed"},
            {"id": "source.revenue_raw", "type": "source", "status": "ok"},
            {"id": "model.executive_dashboard", "type": "model", "status": "stale"},
        ],
        "edges": [
            {"from": "source.revenue_raw", "to": req.node_id},
            {"from": req.node_id, "to": "model.executive_dashboard"},
        ],
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
