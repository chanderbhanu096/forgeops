"""
Knowledge MCP Server.

Tools:
  - search_runbooks         — search operational runbooks
  - get_architecture_decision — retrieve a specific ADR
  - search_incidents        — find similar past incidents
  - search_documentation    — search official docs index
"""
from __future__ import annotations

import os
from typing import Any

import structlog
from fastapi import FastAPI, Header, HTTPException, status
from pydantic import BaseModel

log = structlog.get_logger(__name__)
MCP_SECRET = os.environ.get("MCP_SECRET", "forgeops_mcp_dev")

app = FastAPI(title="ForgeOps Knowledge MCP Server", version="1.0.0")


def verify_auth(authorization: str | None) -> None:
    if not authorization or authorization != f"Bearer {MCP_SECRET}":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)


class SearchRequest(BaseModel):
    query: str
    limit: int = 5


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "server": "mcp-knowledge"}


@app.post("/tools/search_runbooks")
async def search_runbooks(
    req: SearchRequest,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    verify_auth(authorization)
    # Stub — pgvector semantic search over runbook embeddings in v2
    return {
        "query": req.query,
        "results": [
            {
                "title": "Revenue Pipeline Failure Runbook",
                "url": "/runbooks/revenue-pipeline-failure.md",
                "score": 0.91,
                "excerpt": "When the customer revenue pipeline fails, first check the "
                           "schema registry for upstream column changes...",
            }
        ],
    }


@app.post("/tools/search_incidents")
async def search_incidents(
    req: SearchRequest,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    verify_auth(authorization)
    # Stub — returns similar past incidents from episodic memory
    return {
        "query": req.query,
        "incidents": [
            {
                "id": "INC-2023-0441",
                "title": "Revenue metric drop following schema migration",
                "resolved_at": "2023-09-12T14:30:00Z",
                "root_cause": "Column renamed from revenue_usd to revenue_eur without updating downstream models",
                "resolution": "Updated three dbt models and added schema contract tests",
                "similarity": 0.88,
            }
        ],
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
