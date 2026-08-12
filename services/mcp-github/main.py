"""GitHub MCP server with read-only GitHub App authentication by default."""
from __future__ import annotations

import base64
import os
import time
from datetime import datetime
from typing import Any
from urllib.parse import quote

import httpx
import jwt
import structlog
from fastapi import FastAPI, Header, HTTPException, status
from pydantic import BaseModel, Field

log = structlog.get_logger(__name__)

GITHUB_API = os.environ.get("GITHUB_API_URL", "https://api.github.com").rstrip("/")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "").strip()
GITHUB_APP_ID = os.environ.get("FORGEOPS_GITHUB_APP_ID", "").strip()
GITHUB_APP_PRIVATE_KEY = os.environ.get("FORGEOPS_GITHUB_APP_PRIVATE_KEY", "").strip()
GITHUB_INSTALLATION_ID = os.environ.get("FORGEOPS_GITHUB_INSTALLATION_ID", "").strip()
MCP_SECRET = os.environ.get("MCP_SECRET", "forgeops_mcp_dev")
ALLOW_GITHUB_WRITES = os.environ.get("ALLOW_GITHUB_WRITES", "false").lower() == "true"

app = FastAPI(title="ForgeOps GitHub MCP Server", version="2.0.0")
_installation_token: str | None = None
_installation_token_expires_at = 0.0


class RepositoryRequest(BaseModel):
    owner: str = Field(min_length=1, max_length=100)
    repo: str = Field(min_length=1, max_length=100)
    ref: str | None = Field(default=None, max_length=250)


class ReadFileRequest(RepositoryRequest):
    path: str = Field(min_length=1, max_length=1000)


class CreateBranchRequest(BaseModel):
    owner: str = Field(min_length=1)
    repo: str = Field(min_length=1)
    branch: str = Field(min_length=1)
    from_ref: str = Field(default="main", min_length=1)


class CreatePRRequest(BaseModel):
    owner: str = Field(min_length=1)
    repo: str = Field(min_length=1)
    title: str = Field(min_length=1)
    body: str
    head: str = Field(min_length=1)
    base: str = Field(default="main", min_length=1)
    draft: bool = True


def verify_auth(authorization: str | None) -> None:
    if not authorization or authorization != f"Bearer {MCP_SECRET}":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorised")


def require_writes() -> None:
    if not ALLOW_GITHUB_WRITES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="GitHub writes are disabled. Enable ALLOW_GITHUB_WRITES explicitly.",
        )


async def _installation_access_token() -> str:
    global _installation_token, _installation_token_expires_at
    now = time.time()
    if _installation_token and now < _installation_token_expires_at - 90:
        return _installation_token

    if GITHUB_APP_ID and GITHUB_APP_PRIVATE_KEY and GITHUB_INSTALLATION_ID:
        app_jwt = jwt.encode(
            {"iat": int(now) - 60, "exp": int(now) + 540, "iss": GITHUB_APP_ID},
            GITHUB_APP_PRIVATE_KEY.replace("\\n", "\n"),
            algorithm="RS256",
        )
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{GITHUB_API}/app/installations/{GITHUB_INSTALLATION_ID}/access_tokens",
                headers={
                    "Authorization": f"Bearer {app_jwt}",
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                    "User-Agent": "ForgeOps-MCP",
                },
            )
            response.raise_for_status()
            payload = response.json()
        token = str(payload.get("token") or "")
        if not token:
            raise RuntimeError("GitHub App token exchange returned no token")
        _installation_token = token
        expires_at = str(payload.get("expires_at") or "")
        try:
            expiry = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
            _installation_token_expires_at = expiry.timestamp()
        except ValueError:
            _installation_token_expires_at = now + 3000
        return token

    if GITHUB_TOKEN:
        return GITHUB_TOKEN
    raise RuntimeError("GitHub App credentials are not configured")


async def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {await _installation_access_token()}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "ForgeOps-MCP",
    }


async def _gh_request(
    method: str,
    path: str,
    *,
    params: dict[str, str] | None = None,
    body: dict[str, Any] | None = None,
) -> Any:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.request(
            method,
            f"{GITHUB_API}{path}",
            headers=await _headers(),
            params=params,
            json=body,
        )
        response.raise_for_status()
        return response.json()


@app.get("/health")
async def health() -> dict[str, str]:
    mode = "github_app" if GITHUB_APP_ID else "token" if GITHUB_TOKEN else "unconfigured"
    return {"status": "ok", "server": "mcp-github", "authentication": mode}


@app.get("/tools/list_repositories")
async def list_repositories(
    per_page: int = 100,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    verify_auth(authorization)
    data = await _gh_request(
        "GET",
        "/installation/repositories",
        params={"per_page": str(min(max(per_page, 1), 100))},
    )
    repositories = data.get("repositories", []) if isinstance(data, dict) else []
    return {
        "repositories": [
            {
                "owner": item["owner"]["login"],
                "name": item["name"],
                "full_name": item["full_name"],
                "private": item["private"],
                "default_branch": item.get("default_branch"),
                "url": item.get("html_url"),
            }
            for item in repositories
        ]
    }


@app.post("/tools/repository_info")
async def repository_info(
    req: RepositoryRequest,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    verify_auth(authorization)
    repo = await _gh_request("GET", f"/repos/{req.owner}/{req.repo}")
    branch = req.ref or repo.get("default_branch") or "main"
    commit = await _gh_request(
        "GET",
        f"/repos/{req.owner}/{req.repo}/commits/{quote(str(branch), safe='')}",
    )
    return {
        "owner": req.owner,
        "repo": req.repo,
        "url": repo.get("html_url"),
        "default_branch": repo.get("default_branch"),
        "resolved_ref": branch,
        "commit_sha": commit.get("sha"),
        "tree_sha": ((commit.get("commit") or {}).get("tree") or {}).get("sha"),
        "private": repo.get("private"),
    }


@app.post("/tools/list_tree")
async def list_tree(
    req: RepositoryRequest,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    verify_auth(authorization)
    repo = await _gh_request("GET", f"/repos/{req.owner}/{req.repo}")
    branch = req.ref or repo.get("default_branch") or "main"
    commit = await _gh_request(
        "GET",
        f"/repos/{req.owner}/{req.repo}/commits/{quote(str(branch), safe='')}",
    )
    tree_sha = ((commit.get("commit") or {}).get("tree") or {}).get("sha")
    if not tree_sha:
        raise HTTPException(status_code=502, detail="GitHub returned no tree SHA")
    tree = await _gh_request(
        "GET",
        f"/repos/{req.owner}/{req.repo}/git/trees/{tree_sha}",
        params={"recursive": "1"},
    )
    return {
        "commit_sha": commit.get("sha"),
        "tree_sha": tree_sha,
        "truncated": bool(tree.get("truncated", False)),
        "entries": tree.get("tree", []),
    }


@app.post("/tools/read_file")
async def read_file(
    req: ReadFileRequest,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    verify_auth(authorization)
    ref = req.ref or "main"
    data = await _gh_request(
        "GET",
        f"/repos/{req.owner}/{req.repo}/contents/{quote(req.path, safe='/')}",
        params={"ref": ref},
    )
    content_b64 = data.get("content", "")
    content = base64.b64decode(content_b64).decode("utf-8", errors="replace")
    return {
        "path": req.path,
        "ref": ref,
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
    require_writes()
    ref_data = await _gh_request(
        "GET",
        f"/repos/{req.owner}/{req.repo}/git/ref/heads/{quote(req.from_ref, safe='')}",
    )
    sha = ref_data["object"]["sha"]
    result = await _gh_request(
        "POST",
        f"/repos/{req.owner}/{req.repo}/git/refs",
        body={"ref": f"refs/heads/{req.branch}", "sha": sha},
    )
    return {"branch": req.branch, "sha": sha, "url": result.get("url")}


@app.post("/tools/create_pull_request")
async def create_pull_request(
    req: CreatePRRequest,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    verify_auth(authorization)
    require_writes()
    result = await _gh_request(
        "POST",
        f"/repos/{req.owner}/{req.repo}/pulls",
        body={
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
    params = {"branch": branch} if branch else None
    data = await _gh_request(
        "GET",
        f"/repos/{owner}/{repo}/actions/runs",
        params=params,
    )
    runs = data.get("workflow_runs", [])[:10]
    return {
        "runs": [
            {
                "id": run["id"],
                "name": run["name"],
                "status": run["status"],
                "conclusion": run.get("conclusion"),
                "created_at": run["created_at"],
                "url": run["html_url"],
            }
            for run in runs
        ]
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
