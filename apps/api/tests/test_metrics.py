"""
Tests for the Prometheus /metrics endpoint.
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_metrics_returns_200(client: AsyncClient) -> None:
    resp = await client.get("/metrics")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_metrics_content_type(client: AsyncClient) -> None:
    resp = await client.get("/metrics")
    assert "text/plain" in resp.headers["content-type"]


@pytest.mark.asyncio
async def test_metrics_contains_expected_families(client: AsyncClient) -> None:
    resp = await client.get("/metrics")
    body = resp.text
    assert "forgeops_missions_total" in body
    assert "forgeops_missions_active" in body
    assert "forgeops_model_cost_usd_total" in body
    assert "forgeops_approvals_pending" in body


@pytest.mark.asyncio
async def test_metrics_zero_values_on_empty_db(client: AsyncClient) -> None:
    """With a fresh in-memory database all gauges should be zero."""
    resp = await client.get("/metrics")
    body = resp.text
    # active missions — empty DB means 0
    active_line = next(
        (ln for ln in body.splitlines() if ln.startswith("forgeops_missions_active ")),
        None,
    )
    assert active_line is not None
    assert active_line.endswith("0")

    # pending approvals — empty DB means 0
    pending_line = next(
        (ln for ln in body.splitlines() if ln.startswith("forgeops_approvals_pending ")),
        None,
    )
    assert pending_line is not None
    assert pending_line.endswith("0")
