"""Mission execution must publish every runtime event to SSE."""
import uuid
from collections.abc import AsyncIterator
from typing import Any

import pytest

from forgeops.api.routes.missions import _run_mission


class _SessionContext:
    async def __aenter__(self) -> object:
        return object()

    async def __aexit__(self, *_: object) -> None:
        return None


class _SessionFactory:
    def __call__(self) -> _SessionContext:
        return _SessionContext()


@pytest.mark.asyncio
async def test_run_mission_publishes_runtime_events(monkeypatch: pytest.MonkeyPatch) -> None:
    mission_id = uuid.uuid4()
    published: list[tuple[uuid.UUID, str, dict[str, Any]]] = []

    class FakeRuntime:
        def __init__(self, _db: object, received_id: uuid.UUID) -> None:
            assert received_id == mission_id

        async def run(self) -> AsyncIterator[dict[str, Any]]:
            yield {"type": "state_starting", "data": {"state": "plan_generation"}}
            yield {"type": "completed", "data": {"state": "completed"}}

    async def fake_publish(
        received_id: uuid.UUID,
        event_type: str,
        data: dict[str, Any],
    ) -> None:
        published.append((received_id, event_type, data))

    monkeypatch.setattr("forgeops.agent.runtime.AgentRuntime", FakeRuntime)
    monkeypatch.setattr("forgeops.api.routes.sse.publish_event", fake_publish)
    monkeypatch.setattr(
        "forgeops.db.get_session_factory",
        lambda: _SessionFactory(),
    )

    await _run_mission(mission_id)

    assert published == [
        (mission_id, "state_starting", {"state": "plan_generation"}),
        (mission_id, "completed", {"state": "completed"}),
    ]
