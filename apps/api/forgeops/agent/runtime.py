"""ForgeOps persistent mission state-machine runtime."""
from __future__ import annotations

import asyncio
import time
import uuid
from collections.abc import AsyncGenerator
from typing import Any

import structlog
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from forgeops.agent.context import MissionContext
from forgeops.agent.demo_scenario import demo_state_update
from forgeops.agent.handlers import (
    handle_environment_discovery,
    handle_evidence_collection,
    handle_execution,
    handle_hypothesis_creation,
    handle_hypothesis_verification,
    handle_plan_generation,
    handle_post_action_monitoring,
    handle_sandbox_execution,
    handle_solution_generation,
    handle_test_and_review,
)
from forgeops.agent.model_selection import reset_model_selection, set_model_selection
from forgeops.approval_service import ensure_pending_approval
from forgeops.config import get_settings
from forgeops.models.orm import AgentState, Mission, MissionStatus, StateTransition

log = structlog.get_logger(__name__)

TRANSITIONS: dict[AgentState | None, list[AgentState]] = {
    None: [AgentState.mission_received],
    AgentState.mission_received: [AgentState.environment_discovery, AgentState.failed],
    AgentState.environment_discovery: [AgentState.plan_generation, AgentState.failed],
    AgentState.plan_generation: [AgentState.evidence_collection, AgentState.failed],
    AgentState.evidence_collection: [AgentState.hypothesis_creation, AgentState.failed],
    AgentState.hypothesis_creation: [
        AgentState.hypothesis_verification,
        AgentState.failed,
    ],
    AgentState.hypothesis_verification: [
        AgentState.solution_generation,
        AgentState.evidence_collection,
        AgentState.failed,
    ],
    AgentState.solution_generation: [AgentState.sandbox_execution, AgentState.failed],
    AgentState.sandbox_execution: [AgentState.test_and_review, AgentState.failed],
    AgentState.test_and_review: [
        AgentState.human_approval,
        AgentState.solution_generation,
        AgentState.failed,
    ],
    AgentState.human_approval: [AgentState.execution, AgentState.failed],
    AgentState.execution: [AgentState.post_action_monitoring, AgentState.failed],
    AgentState.post_action_monitoring: [AgentState.completed, AgentState.failed],
    AgentState.completed: [],
    AgentState.failed: [],
}

HANDLERS = {
    AgentState.environment_discovery: handle_environment_discovery,
    AgentState.plan_generation: handle_plan_generation,
    AgentState.evidence_collection: handle_evidence_collection,
    AgentState.hypothesis_creation: handle_hypothesis_creation,
    AgentState.hypothesis_verification: handle_hypothesis_verification,
    AgentState.solution_generation: handle_solution_generation,
    AgentState.sandbox_execution: handle_sandbox_execution,
    AgentState.test_and_review: handle_test_and_review,
    AgentState.execution: handle_execution,
    AgentState.post_action_monitoring: handle_post_action_monitoring,
}


class BudgetExceededError(RuntimeError):
    """Raised when a mission exhausts its configured budget."""


class InvalidTransitionError(RuntimeError):
    """Raised when a handler attempts an illegal state transition."""


class AgentRuntime:
    """Execute one mission as a durable state machine."""

    def __init__(self, db: AsyncSession, mission_id: uuid.UUID) -> None:
        self._db = db
        self._mission_id = mission_id
        self._settings = get_settings()
        self._log = log.bind(mission_id=str(mission_id))

    async def run(self) -> AsyncGenerator[dict[str, Any], None]:
        """Run using the provider/model stored on this mission."""
        mission = await self._load_mission()
        token = set_model_selection(mission.llm_provider, mission.llm_model)
        self._log = self._log.bind(
            llm_provider=mission.llm_provider,
            llm_model=mission.llm_model,
        )
        try:
            async for event in self._run_selected(mission):
                yield event
        finally:
            reset_model_selection(token)

    async def _run_selected(
        self, mission: Mission
    ) -> AsyncGenerator[dict[str, Any], None]:
        ctx = await MissionContext.from_mission(mission)
        start_time = time.monotonic()
        is_demo = mission.llm_provider == "demo"

        if is_demo:
            self._log.info("demo_mode_enabled")

        if mission.current_state is None:
            await self._transition(mission, AgentState.mission_received, ctx)
            yield self._event("state_changed", {"state": AgentState.mission_received})

        while mission.current_state not in (AgentState.completed, AgentState.failed):
            elapsed = time.monotonic() - start_time
            if mission.steps_used >= mission.max_steps:
                raise BudgetExceededError(
                    f"Step budget exhausted ({mission.max_steps} steps)"
                )
            if mission.cost_usd_used >= mission.max_cost_usd:
                raise BudgetExceededError(
                    f"Cost budget exhausted (${mission.max_cost_usd:.2f})"
                )
            if elapsed > mission.max_duration_seconds:
                raise BudgetExceededError(
                    f"Time budget exhausted ({mission.max_duration_seconds}s)"
                )

            fresh = await self._load_mission()
            if fresh.status == MissionStatus.paused:
                self._log.info("mission_paused", state=str(mission.current_state))
                yield self._event("paused", {"state": str(mission.current_state)})
                return

            if (
                mission.current_state == AgentState.human_approval
                and fresh.status != MissionStatus.approved
            ):
                if is_demo:
                    await self._db.execute(
                        update(Mission)
                        .where(Mission.id == mission.id)
                        .values(status=MissionStatus.approved)
                    )
                    await self._db.commit()
                    mission.status = MissionStatus.approved
                    self._log.info("demo_approval_granted")
                else:
                    approval = await ensure_pending_approval(self._db, mission, ctx)
                    self._log.info(
                        "awaiting_human_approval",
                        approval_id=str(approval.id),
                    )
                    yield self._event(
                        "awaiting_approval",
                        {"approval_id": str(approval.id)},
                    )
                    return

            next_state = self._next_runnable_state(mission.current_state)
            if next_state is None:
                break

            self._log.info("state_starting", state=next_state)
            yield self._event("state_starting", {"state": next_state})

            try:
                if is_demo:
                    ctx.update(demo_state_update(next_state, ctx))
                    await asyncio.sleep(0.25)
                else:
                    handler = HANDLERS.get(next_state)
                    if handler is not None:
                        result = await asyncio.wait_for(
                            handler(ctx, self._db),
                            timeout=self._settings.default_max_duration_seconds,
                        )
                        ctx.update(result)

                await self._transition(mission, next_state, ctx)
                await self._record_step(mission, ctx.last_cost_usd)
                yield self._event(
                    "state_changed",
                    {
                        "state": next_state,
                        "steps_used": mission.steps_used,
                        "cost_usd": mission.cost_usd_used,
                        "provider": mission.llm_provider,
                        "model": mission.llm_model,
                    },
                )

            except TimeoutError:
                await self._fail(mission, ctx, f"Handler timed out in state {next_state}")
                yield self._event("failed", {"reason": "timeout", "state": next_state})
                return

            except Exception as exc:
                self._log.exception("handler_error", state=next_state, error=str(exc))
                await self._fail(mission, ctx, str(exc))
                yield self._event("failed", {"reason": str(exc), "state": next_state})
                return

        yield self._event(
            "completed" if mission.current_state == AgentState.completed else "failed",
            {"state": str(mission.current_state)},
        )

    async def resume_after_approval(self) -> AsyncGenerator[dict[str, Any], None]:
        """Resume from the approval gate without skipping the execution handler."""
        mission = await self._load_mission()
        if mission.current_state != AgentState.human_approval:
            return
        if mission.status != MissionStatus.approved:
            return

        token = set_model_selection(mission.llm_provider, mission.llm_model)
        try:
            async for event in self._run_selected(mission):
                yield event
        finally:
            reset_model_selection(token)

    def _next_runnable_state(self, current: AgentState | None) -> AgentState | None:
        for successor in TRANSITIONS.get(current, []):
            if successor != AgentState.failed:
                return successor
        return None

    async def _transition(
        self,
        mission: Mission,
        to_state: AgentState,
        ctx: MissionContext,
        trigger: str | None = None,
    ) -> None:
        allowed = TRANSITIONS.get(mission.current_state, [])
        if to_state not in allowed:
            raise InvalidTransitionError(
                f"Transition {mission.current_state} → {to_state} is not allowed"
            )

        transition = StateTransition(
            mission_id=mission.id,
            from_state=mission.current_state,
            to_state=to_state,
            trigger=trigger,
            extra=ctx.to_checkpoint_metadata(),
        )
        self._db.add(transition)

        new_status = self._state_to_status(to_state)
        await self._db.execute(
            update(Mission)
            .where(Mission.id == mission.id)
            .values(
                current_state=to_state,
                checkpoint=ctx.to_checkpoint(),
                status=new_status,
            )
        )
        await self._db.commit()
        mission.current_state = to_state
        mission.status = new_status

        self._log.info(
            "state_transition",
            from_state=str(transition.from_state),
            to_state=to_state,
        )

        try:
            from forgeops.observability import trace_state_transition

            trace_state_transition(
                mission_id=str(mission.id),
                from_state=str(transition.from_state),
                to_state=to_state,
                metadata=ctx.to_checkpoint_metadata(),
            )
        except Exception:
            pass

    async def _fail(
        self, mission: Mission, ctx: MissionContext, reason: str
    ) -> None:
        await self._db.execute(
            update(Mission)
            .where(Mission.id == mission.id)
            .values(
                current_state=AgentState.failed,
                status=MissionStatus.failed,
                error=reason,
            )
        )
        await self._db.commit()
        mission.current_state = AgentState.failed
        mission.status = MissionStatus.failed

    async def _record_step(self, mission: Mission, cost_usd: float) -> None:
        new_steps = mission.steps_used + 1
        new_cost = mission.cost_usd_used + cost_usd
        await self._db.execute(
            update(Mission)
            .where(Mission.id == mission.id)
            .values(steps_used=new_steps, cost_usd_used=new_cost)
        )
        await self._db.commit()
        mission.steps_used = new_steps
        mission.cost_usd_used = new_cost

    async def _load_mission(self) -> Mission:
        result = await self._db.execute(
            select(Mission).where(Mission.id == self._mission_id)
        )
        mission = result.scalar_one_or_none()
        if mission is None:
            raise ValueError(f"Mission {self._mission_id} not found")
        return mission

    @staticmethod
    def _state_to_status(state: AgentState) -> MissionStatus:
        if state == AgentState.completed:
            return MissionStatus.completed
        if state == AgentState.failed:
            return MissionStatus.failed
        if state == AgentState.human_approval:
            return MissionStatus.awaiting_approval
        return MissionStatus.running

    @staticmethod
    def _event(event_type: str, data: dict[str, Any]) -> dict[str, Any]:
        return {"type": event_type, "data": data}
