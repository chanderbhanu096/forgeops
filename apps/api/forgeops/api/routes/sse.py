"""
Server-Sent Events (SSE) streaming — real-time mission progress to the UI.

The UI subscribes to /api/v1/stream/{mission_id} and receives events as the
agent runtime progresses through state machine transitions.
"""
from __future__ import annotations

import asyncio
import json
import uuid
from collections.abc import AsyncGenerator
from typing import Any

import structlog
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from forgeops.cache import get_redis

router = APIRouter()
log = structlog.get_logger(__name__)

# Redis pub/sub channel pattern: forgeops:mission:{id}:events
_CHANNEL_PATTERN = "forgeops:mission:{mission_id}:events"


def mission_channel(mission_id: uuid.UUID) -> str:
    return _CHANNEL_PATTERN.format(mission_id=str(mission_id))


async def publish_event(
    mission_id: uuid.UUID, event_type: str, data: dict[str, Any]
) -> None:
    """Publish a mission event to Redis for SSE delivery."""
    try:
        redis = await get_redis()
        payload = json.dumps({"type": event_type, "data": data})
        await redis.publish(mission_channel(mission_id), payload)
    except Exception as exc:
        log.warning("sse_publish_failed", error=str(exc))


async def _event_generator(
    mission_id: uuid.UUID,
) -> AsyncGenerator[str, None]:
    """Subscribe to the Redis channel and yield SSE-formatted events."""
    redis = await get_redis()
    pubsub = redis.pubsub()
    channel = mission_channel(mission_id)

    await pubsub.subscribe(channel)
    log.info("sse_subscribed", channel=channel)

    try:
        while True:
            message = await asyncio.wait_for(pubsub.get_message(ignore_subscribe_messages=True), timeout=30.0)
            if message and message["type"] == "message":
                raw = message["data"]
                yield f"data: {raw}\n\n"
            else:
                # Keepalive ping
                yield ": ping\n\n"
    except asyncio.TimeoutError:
        yield "data: {\"type\": \"timeout\"}\n\n"
    except Exception as exc:
        log.error("sse_stream_error", error=str(exc))
    finally:
        await pubsub.unsubscribe(channel)
        await pubsub.aclose()


@router.get("/{mission_id}")
async def stream_mission(mission_id: uuid.UUID) -> StreamingResponse:
    """
    SSE stream for a mission. The UI connects once and receives all
    state machine events until the mission completes.
    """
    return StreamingResponse(
        _event_generator(mission_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
