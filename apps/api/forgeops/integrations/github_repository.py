"""Read-only GitHub repository inspection backed by a GitHub App installation."""
from __future__ import annotations

import base64
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import PurePosixPath
from typing import Any
from urllib.parse import quote, urlparse

import httpx
import jwt
import structlog

from forgeops.config import get_settings

log = structlog.get_logger(__name__)

_BINARY_SUFFIXES = {
    ".7z",
    ".avi",
    ".bin",
    ".bmp",
    ".class",
    ".dll",
    ".dylib",
    ".exe",
    ".gif",
    ".gz",
    ".ico",
    ".jpeg",
    ".jpg",
    ".lockb",
    ".mov",
    ".mp3",
    ".mp4",
    ".pdf",
    ".png",
    ".pyc",
    ".so",
    ".tar",
    ".tgz",
    ".ttf",
    ".webp",
    ".woff",
    ".woff2",
    ".zip",
}

_PRIORITY_NAMES = {
    "readme.md": 140,
    "pyproject.toml": 125,
    "package.json": 125,
    "docker-compose.yml": 120,
    "docker-compose.yaml": 120,
    "compose.yml": 120,
    "compose.yaml": 120,
    "dockerfile": 110,
    "requirements.txt": 105,
    "poetry.lock": 70,
    "package-lock.json": 65,
    "pnpm-lock.yaml": 65,
    "yarn.lock": 65,
    ".env.example": 95,
    "makefile": 90,
    "justfile": 90,
    "main.py": 85,
    "app.py": 85,
    "index.ts": 80,
    "index.tsx": 80,
    "page.tsx": 75,
}


@dataclass(frozen=True, slots=True)
class RepositoryIdentity:
    owner: str
    name: str
    url: str
    default_branch: str
    commit_sha: str


@dataclass(frozen=True, slots=True)
class RepositoryFile:
    path: str
    content: str
    size: int
    citation: str


@dataclass(frozen=True, slots=True)
class RepositorySnapshot:
    identity: RepositoryIdentity
    files: list[RepositoryFile]
    tree_file_count: int
    tree_truncated: bool
    detected_stack: list[str]


def parse_github_repository_url(repository_url: str) -> tuple[str, str]:
    """Parse and validate a github.com owner/repository URL."""
    parsed = urlparse(repository_url.strip())
    if parsed.scheme not in {"http", "https"} or parsed.netloc.lower() != "github.com":
        raise ValueError("Repository URL must use https://github.com/owner/repository")
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) < 2:
        raise ValueError("Repository URL must include an owner and repository name")
    owner = parts[0]
    repo = parts[1].removesuffix(".git")
    if not owner or not repo:
        raise ValueError("Repository owner and name must not be empty")
    return owner, repo


def normalise_github_repository_url(repository_url: str) -> str:
    owner, repo = parse_github_repository_url(repository_url)
    return f"https://github.com/{owner}/{repo}"


class GitHubRepositoryClient:
    """Retrieve repository metadata and selected text files without write access."""

    def __init__(self) -> None:
        self._settings = get_settings()
        self._installation_token: str | None = None
        self._installation_token_expires_at = 0.0

    async def inspect(
        self,
        repository_url: str,
        question: str,
        *,
        max_files: int = 20,
        max_file_bytes: int = 180_000,
    ) -> RepositorySnapshot:
        owner, repo = parse_github_repository_url(repository_url)
        metadata = await self._request("GET", f"/repos/{owner}/{repo}")
        default_branch = str(metadata.get("default_branch") or "main")
        commit = await self._request(
            "GET",
            f"/repos/{owner}/{repo}/commits/{quote(default_branch, safe='')}",
        )
        commit_sha = str(commit.get("sha") or "")
        tree_sha = str(((commit.get("commit") or {}).get("tree") or {}).get("sha") or "")
        if not commit_sha or not tree_sha:
            raise RuntimeError("GitHub did not return the repository commit and tree identity")

        tree = await self._request(
            "GET",
            f"/repos/{owner}/{repo}/git/trees/{tree_sha}",
            params={"recursive": "1"},
        )
        entries = [
            entry
            for entry in tree.get("tree", [])
            if entry.get("type") == "blob" and isinstance(entry.get("path"), str)
        ]
        selected = self._select_paths(entries, question, max_files=max_files)

        files: list[RepositoryFile] = []
        for entry in selected:
            path = str(entry["path"])
            size = int(entry.get("size") or 0)
            if size > max_file_bytes or PurePosixPath(path).suffix.lower() in _BINARY_SUFFIXES:
                continue
            try:
                file_data = await self._request(
                    "GET",
                    f"/repos/{owner}/{repo}/contents/{quote(path, safe='/')}",
                    params={"ref": commit_sha},
                )
            except httpx.HTTPStatusError as exc:
                log.warning(
                    "github_file_read_failed",
                    repository=f"{owner}/{repo}",
                    path=path,
                    status=exc.response.status_code,
                )
                continue
            encoded = file_data.get("content")
            if not isinstance(encoded, str):
                continue
            try:
                content = base64.b64decode(encoded).decode("utf-8", errors="replace")
            except (ValueError, TypeError):
                continue
            if not content.strip():
                continue
            line_count = max(1, content.count("\n") + 1)
            files.append(
                RepositoryFile(
                    path=path,
                    content=content,
                    size=int(file_data.get("size") or size),
                    citation=(
                        f"github://{owner}/{repo}@{commit_sha}/{path}:L1-L{line_count}"
                    ),
                )
            )

        if not files:
            raise RuntimeError(
                "GitHub access succeeded, but no readable text files were selected from the repository"
            )

        identity = RepositoryIdentity(
            owner=owner,
            name=repo,
            url=f"https://github.com/{owner}/{repo}",
            default_branch=default_branch,
            commit_sha=commit_sha,
        )
        return RepositorySnapshot(
            identity=identity,
            files=files,
            tree_file_count=len(entries),
            tree_truncated=bool(tree.get("truncated", False)),
            detected_stack=self._detect_stack(files),
        )

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        token = await self._get_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "ForgeOps-AI",
        }
        base_url = self._settings.github_api_url.rstrip("/")
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(
                method,
                f"{base_url}{path}",
                headers=headers,
                params=params,
            )
            response.raise_for_status()
            payload = response.json()
        if not isinstance(payload, dict):
            raise RuntimeError(f"Unexpected GitHub response for {path}")
        return payload

    async def _get_token(self) -> str:
        fallback = self._settings.github_token.get_secret_value().strip()
        app_id = self._settings.github_app_id.strip()
        installation_id = self._settings.github_app_installation_id.strip()
        private_key = self._settings.github_app_private_key.get_secret_value().strip()

        if app_id and installation_id and private_key:
            now = time.time()
            if (
                self._installation_token
                and now < self._installation_token_expires_at - 90
            ):
                return self._installation_token
            app_jwt = jwt.encode(
                {
                    "iat": int(now) - 60,
                    "exp": int(now) + 540,
                    "iss": app_id,
                },
                private_key.replace("\\n", "\n"),
                algorithm="RS256",
            )
            base_url = self._settings.github_api_url.rstrip("/")
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{base_url}/app/installations/{installation_id}/access_tokens",
                    headers={
                        "Authorization": f"Bearer {app_jwt}",
                        "Accept": "application/vnd.github+json",
                        "X-GitHub-Api-Version": "2022-11-28",
                        "User-Agent": "ForgeOps-AI",
                    },
                )
                response.raise_for_status()
                payload = response.json()
            token = str(payload.get("token") or "")
            expires_at = str(payload.get("expires_at") or "")
            if not token:
                raise RuntimeError("GitHub App token exchange returned no installation token")
            self._installation_token = token
            try:
                parsed_expiry = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
                self._installation_token_expires_at = parsed_expiry.timestamp()
            except ValueError:
                self._installation_token_expires_at = now + 3000
            return token

        if fallback:
            return fallback
        raise RuntimeError(
            "GitHub access is not configured. Set FORGEOPS_GITHUB_APP_ID, "
            "FORGEOPS_GITHUB_APP_PRIVATE_KEY and FORGEOPS_GITHUB_INSTALLATION_ID."
        )

    @staticmethod
    def _select_paths(
        entries: list[dict[str, Any]],
        question: str,
        *,
        max_files: int,
    ) -> list[dict[str, Any]]:
        keywords = {
            token
            for token in question.lower().replace("-", " ").replace("_", " ").split()
            if len(token) >= 4
        }

        def score(entry: dict[str, Any]) -> tuple[int, str]:
            path = str(entry["path"])
            lower = path.lower()
            name = PurePosixPath(path).name.lower()
            suffix = PurePosixPath(path).suffix.lower()
            value = _PRIORITY_NAMES.get(name, 0)
            if lower.startswith(".github/workflows/"):
                value += 100
            if lower.startswith("docs/"):
                value += 45
            if any(part in lower for part in ("src/", "app/", "api/", "backend/", "frontend/")):
                value += 28
            if suffix in {".py", ".ts", ".tsx", ".js", ".jsx", ".sql", ".yaml", ".yml"}:
                value += 20
            value += 18 * sum(1 for keyword in keywords if keyword in lower)
            depth = path.count("/")
            value -= min(depth, 8)
            return value, path

        candidates = [
            entry
            for entry in entries
            if PurePosixPath(str(entry["path"])).suffix.lower() not in _BINARY_SUFFIXES
        ]
        return sorted(candidates, key=score, reverse=True)[:max_files]

    @staticmethod
    def _detect_stack(files: list[RepositoryFile]) -> list[str]:
        paths = "\n".join(file.path.lower() for file in files)
        sample = "\n".join(file.content[:30_000].lower() for file in files)
        combined = f"{paths}\n{sample}"
        checks = [
            ("Python", ".py" in paths or "pyproject.toml" in paths),
            ("TypeScript", ".ts" in paths or ".tsx" in paths),
            ("JavaScript", ".js" in paths or "package.json" in paths),
            ("FastAPI", "fastapi" in combined),
            ("Django", "django" in combined),
            ("Next.js", "next" in combined and "package.json" in paths),
            ("React", "react" in combined),
            ("PostgreSQL", "postgres" in combined or "asyncpg" in combined),
            ("Redis", "redis" in combined),
            ("Docker", "dockerfile" in paths or "docker-compose" in paths),
            ("GitHub Actions", ".github/workflows/" in paths),
            ("Terraform", ".tf" in paths or "terraform" in combined),
            ("dbt", "dbt_project.yml" in paths or "dbt" in combined),
            ("Machine Learning", "scikit-learn" in combined or "sklearn" in combined),
        ]
        return [name for name, present in checks if present]
