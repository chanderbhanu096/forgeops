"""
Skills routes — discovery endpoint.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from forgeops.skills.registry import get_skill_registry

router = APIRouter()


@router.get("", response_model=list[dict[str, Any]])
async def list_skills() -> list[dict[str, Any]]:
    """Return all registered skills."""
    return get_skill_registry().list_skills()


@router.get("/{name}")
async def get_skill(name: str, version: str | None = None) -> dict[str, Any]:
    from fastapi import HTTPException

    spec = get_skill_registry().get(name, version)
    if spec is None:
        raise HTTPException(status_code=404, detail=f"Skill '{name}' not found")
    return spec.model_dump()
