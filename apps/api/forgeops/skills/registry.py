"""
Skill registry — loads, validates and serves versioned skill definitions.

Skills are defined as YAML files in the skills/ directory.
The registry is an in-process singleton; skill definitions are also
persisted to the skills table for history and audit.
"""
from __future__ import annotations

import importlib.resources
from pathlib import Path
from typing import Any

import structlog
import yaml
from pydantic import BaseModel, Field

log = structlog.get_logger(__name__)

# ── Skill models ──────────────────────────────────────────────────────────────


class SkillPermissions(BaseModel):
    filesystem: str = "sandbox_only"       # none | sandbox_only | read_only | read_write
    database: str = "read_only"            # none | read_only | read_write
    network: str = "restricted"            # none | restricted | unrestricted


class SkillSpec(BaseModel):
    name: str
    version: str
    description: str
    required_tools: list[str] = Field(default_factory=list)
    permissions: SkillPermissions = Field(default_factory=SkillPermissions)
    inputs: dict[str, str] = Field(default_factory=dict)
    outputs: dict[str, str] = Field(default_factory=dict)
    dependencies: list[str] = Field(default_factory=list)

    def requires_tool(self, tool: str) -> bool:
        return tool in self.required_tools

    def allows_filesystem(self, level: str) -> bool:
        order = ["none", "sandbox_only", "read_only", "read_write"]
        granted = order.index(self.permissions.filesystem)
        required = order.index(level)
        return granted >= required


# ── Registry ──────────────────────────────────────────────────────────────────


class SkillRegistry:
    """
    Loads all skill YAML files from the skills directory and provides
    lookup by name and version.
    """

    def __init__(self) -> None:
        self._skills: dict[str, dict[str, SkillSpec]] = {}  # name → version → spec

    def load_from_directory(self, path: Path) -> int:
        """Load all *.yaml files from a directory. Returns count loaded."""
        if not path.exists():
            log.warning("skills_directory_not_found", path=str(path))
            return 0

        loaded = 0
        for yaml_file in sorted(path.glob("*.yaml")):
            try:
                self._load_file(yaml_file)
                loaded += 1
            except Exception as exc:
                log.error("skill_load_failed", file=str(yaml_file), error=str(exc))

        log.info("skills_loaded", count=loaded, directory=str(path))
        return loaded

    def _load_file(self, path: Path) -> None:
        raw = yaml.safe_load(path.read_text())
        spec = SkillSpec.model_validate(raw)
        if spec.name not in self._skills:
            self._skills[spec.name] = {}
        self._skills[spec.name][spec.version] = spec

    # ── Lookup ────────────────────────────────────────────────────────────────

    def get(self, name: str, version: str | None = None) -> SkillSpec | None:
        """Get a skill by name. Returns latest version if version is None."""
        if name not in self._skills:
            return None
        versions = self._skills[name]
        if version:
            return versions.get(version)
        # Return the latest semantic version
        latest = sorted(versions.keys(), key=_semver_key)[-1]
        return versions[latest]

    def list_skills(self) -> list[dict[str, Any]]:
        result = []
        for name, versions in self._skills.items():
            latest_version = sorted(versions.keys(), key=_semver_key)[-1]
            spec = versions[latest_version]
            result.append({
                "name": spec.name,
                "version": spec.version,
                "description": spec.description,
                "required_tools": spec.required_tools,
            })
        return result

    def find_for_task(self, task_description: str) -> list[SkillSpec]:
        """Return skills whose name or description keywords match the task."""
        task_lower = task_description.lower()
        matches = []
        for name, versions in self._skills.items():
            latest = sorted(versions.keys(), key=_semver_key)[-1]
            spec = versions[latest]
            if any(word in task_lower for word in name.replace("_", " ").split()):
                matches.append(spec)
        return matches


def _semver_key(version: str) -> tuple[int, ...]:
    """Parse 'X.Y.Z' → (X, Y, Z) for sorting."""
    try:
        return tuple(int(x) for x in version.split("."))
    except ValueError:
        return (0, 0, 0)


# ── Singleton ─────────────────────────────────────────────────────────────────

_registry: SkillRegistry | None = None


def get_skill_registry() -> SkillRegistry:
    global _registry
    if _registry is None:
        _registry = SkillRegistry()
        skills_path = Path(__file__).parent.parent / "skills" / "definitions"
        _registry.load_from_directory(skills_path)
    return _registry
