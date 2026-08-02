"""Tests for the mission API endpoints."""
from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health(client: AsyncClient) -> None:
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_create_mission(client: AsyncClient, sample_mission: dict) -> None:
    resp = await client.post("/api/v1/missions", json=sample_mission)
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == sample_mission["title"]
    assert data["status"] == "pending"
    assert "id" in data


@pytest.mark.asyncio
async def test_list_missions_empty(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/missions")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_get_mission_not_found(client: AsyncClient) -> None:
    import uuid
    resp = await client.get(f"/api/v1/missions/{uuid.uuid4()}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_create_mission_title_too_short(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/missions",
        json={"title": "x", "description": "long enough description here"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_skills_endpoint(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/skills")
    assert resp.status_code == 200
    skills = resp.json()
    assert isinstance(skills, list)
    names = [s["name"] for s in skills]
    assert "dbt_model_repair" in names
    assert "log_investigation" in names
