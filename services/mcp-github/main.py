"""
GitHub MCP Server — exposes repository tools over HTTP+SSE.

Tools exposed:
  - search_repositories
  - read_file
  - list_directory
  - create_branch
  - apply_patch
  - create_pull_request
  - get_pull_request
  - list_ci_runs

Authentication: Bearer token checked against MCP_SECRET env var.
"""
from __future__ import annotations

import base64
import os
from typing import Any

import httpx
import structlog
from fastapi import FastAPI, Header, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

log = structlog.get_logger(__name__)

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
MCP_SECRET = os.environ.get("MCP_SECRET", "forgeops_mcp_dev")
GITHUB_API = "https://api.github.com"

app = FastAPI(title="ForgeOps GitHub MCP Server", version="1.0.0")

# ── Auth ──────────────────────────────────────────────────────────────────────


def verify_auth(authorization: str | None) -> None:
    if not authorization or authorization != f"Bearer {MCP_SECRET}":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorised")


# ── Tool schemas ──────────────────────────────────────────────────────────────


class ReadFileRequest(BaseModel):
    owner: str
    repo: str
    path: str
    ref: str = "main"


class CreateBranchRequest(BaseModel):
    owner: str
    repo: str
    branch: str
    from_ref: str = "main"


class CreatePRRequest(BaseModel):
    owner: str
    repo: str
    title: str
    body: str
    head: str
    base: str = "main"
    draft: bool = True


class ApplyPatchRequest(BaseModel):
    owner: str
    repo: str
    branch: str
    patch: str
    commit_message: str
    changed_files: list[str]


# ── GitHub client ─────────────────────────────────────────────────────────────


def _gh_headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


async def _gh_get(path: str) -> dict[str, Any]:
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{GITHUB_API}{path}", headers=_gh_headers())
        resp.raise_for_status()
        return resp.json()


async def _gh_post(path: str, body: dict[str, Any]) -> dict[str, Any]:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{GITHUB_API}{path}", json=body, headers=_gh_headers()
        )
        resp.raise_for_status()
        return resp.json()


# ── Tool endpoints ────────────────────────────────────────────────────────────


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "server": "mcp-github"}


@app.post("/tools/read_file")
async def read_file(
    req: ReadFileRequest,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    verify_auth(authorization)
    data = await _gh_get(
        f"/repos/{req.owner}/{req.repo}/contents/{req.path}?ref={req.ref}"
    )
    content_b64 = data.get("content", "")
    content = base64.b64decode(content_b64).decode("utf-8", errors="replace")
    return {
        "path": req.path,
        "content": content,
        "sha": data.get("sha"),
        "size": data.get("size"),
    }


@app.post("/tools/create_branch")
async def create_branch(
    req: CreateBranchRequest,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    verify_auth(authorization)

    # Get SHA of the source ref
    ref_data = await _gh_get(
        f"/repos/{req.owner}/{req.repo}/git/ref/heads/{req.from_ref}"
    )
    sha = ref_data["object"]["sha"]

    result = await _gh_post(
        f"/repos/{req.owner}/{req.repo}/git/refs",
        {"ref": f"refs/heads/{req.branch}", "sha": sha},
    )
    return {"branch": req.branch, "sha": sha, "url": result.get("url")}


@app.post("/tools/create_pull_request")
async def create_pull_request(
    req: CreatePRRequest,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    verify_auth(authorization)
    result = await _gh_post(
        f"/repos/{req.owner}/{req.repo}/pulls",
        {
            "title": req.title,
            "body": req.body,
            "head": req.head,
            "base": req.base,
            "draft": req.draft,
        },
    )
    return {
        "number": result.get("number"),
        "url": result.get("html_url"),
        "state": result.get("state"),
    }


@app.get("/tools/list_ci_runs")
async def list_ci_runs(
    owner: str,
    repo: str,
    branch: str | None = None,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    verify_auth(authorization)
    path = f"/repos/{owner}/{repo}/actions/runs"
    if branch:
        path += f"?branch={branch}"
    data = await _gh_get(path)
    runs = data.get("workflow_runs", [])[:10]
    return {
        "runs": [
            {
                "id": r["id"],
                "name": r["name"],
                "status": r["status"],
                "conclusion": r.get("conclusion"),
                "created_at": r["created_at"],
                "url": r["html_url"],
            }
            for r in runs
        ]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
