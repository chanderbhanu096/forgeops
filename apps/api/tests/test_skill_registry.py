"""Tests for the skill registry."""
from __future__ import annotations

from pathlib import Path

import pytest

from forgeops.skills.registry import SkillRegistry, _semver_key


def _registry_with_definitions() -> SkillRegistry:
    """Load the real skill YAML definitions."""
    reg = SkillRegistry()
    skills_path = Path(__file__).parent.parent / "forgeops" / "skills" / "definitions"
    reg.load_from_directory(skills_path)
    return reg


def test_registry_loads_skills():
    reg = _registry_with_definitions()
    skills = reg.list_skills()
    assert len(skills) >= 3
    names = {s["name"] for s in skills}
    assert "dbt_model_repair" in names
    assert "security_review" in names


def test_registry_get_returns_spec():
    reg = _registry_with_definitions()
    spec = reg.get("dbt_model_repair")
    assert spec is not None
    assert spec.version == "1.0.0"
    assert "repository.read" in spec.required_tools


def test_registry_get_unknown_returns_none():
    reg = _registry_with_definitions()
    assert reg.get("nonexistent_skill") is None


def test_skill_permissions():
    reg = _registry_with_definitions()
    spec = reg.get("dbt_model_repair")
    assert spec is not None
    assert spec.permissions.filesystem == "sandbox_only"
    assert spec.permissions.database == "read_only"


def test_semver_sort():
    versions = ["1.0.0", "2.1.0", "1.10.0", "0.9.0"]
    assert sorted(versions, key=_semver_key) == ["0.9.0", "1.0.0", "1.10.0", "2.1.0"]


def test_find_for_task_returns_relevant_skills():
    reg = _registry_with_definitions()
    results = reg.find_for_task("investigate log errors in the pipeline")
    names = [s.name for s in results]
    assert "log_investigation" in names
