"""
MissionContext — the shared mutable state carried through all agent states.

One context object lives for the duration of a mission. Handlers read
from it and write to it. The runtime persists it as a checkpoint after
every successful state transition.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from forgeops.models.orm import Mission


@dataclass
class Hypothesis:
    id: str
    description: str
    confidence: float          # 0.0 – 1.0
    evidence: list[str]
    rank: int = 0


@dataclass
class VerificationResult:
    hypothesis_id: str
    confirmed: bool
    confidence: float
    findings: list[str]


@dataclass
class PlanStep:
    step_id: str
    description: str
    skill_name: str | None = None
    estimated_cost_usd: float = 0.0
    completed: bool = False


@dataclass
class MissionContext:
    # Identity
    mission_id: uuid.UUID
    title: str
    description: str
    attachments: list[dict[str, Any]] = field(default_factory=list)

    # Plan
    plan: list[PlanStep] = field(default_factory=list)
    current_plan_step: int = 0

    # Environment
    repository_url: str | None = None
    repository_path: str | None = None
    environment_summary: str = ""

    # Evidence
    raw_evidence: list[dict[str, Any]] = field(default_factory=list)
    relevant_files: list[str] = field(default_factory=list)
    log_excerpts: list[str] = field(default_factory=list)

    # Hypotheses
    hypotheses: list[Hypothesis] = field(default_factory=list)
    top_hypothesis: Hypothesis | None = None
    verification_results: list[VerificationResult] = field(default_factory=list)

    # Solution
    proposed_patch: str | None = None           # unified diff
    changed_files: list[str] = field(default_factory=list)
    sandbox_test_output: str | None = None
    test_passed: bool = False
    security_findings: list[dict[str, Any]] = field(default_factory=list)

    # PR
    pull_request_url: str | None = None
    pull_request_number: int | None = None

    # Budget tracking
    last_cost_usd: float = 0.0
    total_model_calls: int = 0

    # Model messages (used by handlers)
    conversation: list[dict[str, Any]] = field(default_factory=list)

    # Arbitrary handler-specific scratchpad
    scratchpad: dict[str, Any] = field(default_factory=dict)

    # ── Factory ───────────────────────────────────────────────────────────────

    @classmethod
    async def from_mission(cls, mission: Mission) -> MissionContext:
        """Restore from a persisted checkpoint, or create fresh."""
        if mission.checkpoint:
            return cls._from_checkpoint(mission.checkpoint, mission)
        return cls(
            mission_id=mission.id,
            title=mission.title,
            description=mission.description,
            attachments=mission.attachments or [],
        )

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_checkpoint(self) -> dict[str, Any]:
        """Serialise context to JSON-safe dict for DB persistence."""
        return {
            "mission_id": str(self.mission_id),
            "title": self.title,
            "description": self.description,
            "attachments": self.attachments,
            "plan": [
                {
                    "step_id": s.step_id,
                    "description": s.description,
                    "skill_name": s.skill_name,
                    "estimated_cost_usd": s.estimated_cost_usd,
                    "completed": s.completed,
                }
                for s in self.plan
            ],
            "current_plan_step": self.current_plan_step,
            "repository_url": self.repository_url,
            "environment_summary": self.environment_summary,
            "hypotheses": [
                {
                    "id": h.id,
                    "description": h.description,
                    "confidence": h.confidence,
                    "evidence": h.evidence,
                    "rank": h.rank,
                }
                for h in self.hypotheses
            ],
            "proposed_patch": self.proposed_patch,
            "changed_files": self.changed_files,
            "test_passed": self.test_passed,
            "pull_request_url": self.pull_request_url,
            "security_findings": self.security_findings,
            "total_model_calls": self.total_model_calls,
            "scratchpad": self.scratchpad,
        }

    def to_checkpoint_metadata(self) -> dict[str, Any]:
        """Lightweight metadata for state transition audit logs."""
        return {
            "plan_step": self.current_plan_step,
            "total_plan_steps": len(self.plan),
            "hypothesis_count": len(self.hypotheses),
            "has_patch": self.proposed_patch is not None,
            "test_passed": self.test_passed,
        }

    def update(self, result: dict[str, Any] | None) -> None:
        """Merge a handler result dict into the context."""
        if not result:
            return
        for key, value in result.items():
            if hasattr(self, key):
                setattr(self, key, value)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def add_evidence(
        self, source: str, content: str, metadata: dict[str, Any] | None = None
    ) -> None:
        self.raw_evidence.append({
            "source": source,
            "content": content,
            "metadata": metadata or {},
        })

    def add_model_cost(self, cost_usd: float) -> None:
        self.last_cost_usd = cost_usd
        self.total_model_calls += 1

    # ── Private ───────────────────────────────────────────────────────────────

    @classmethod
    def _from_checkpoint(cls, cp: dict[str, Any], mission: Mission) -> MissionContext:
        ctx = cls(
            mission_id=mission.id,
            title=cp.get("title", mission.title),
            description=cp.get("description", mission.description),
            attachments=cp.get("attachments", []),
        )
        ctx.plan = [
            PlanStep(
                step_id=s["step_id"],
                description=s["description"],
                skill_name=s.get("skill_name"),
                estimated_cost_usd=s.get("estimated_cost_usd", 0.0),
                completed=s.get("completed", False),
            )
            for s in cp.get("plan", [])
        ]
        ctx.current_plan_step = cp.get("current_plan_step", 0)
        ctx.repository_url = cp.get("repository_url")
        ctx.environment_summary = cp.get("environment_summary", "")
        ctx.hypotheses = [
            Hypothesis(
                id=h["id"],
                description=h["description"],
                confidence=h["confidence"],
                evidence=h["evidence"],
                rank=h.get("rank", 0),
            )
            for h in cp.get("hypotheses", [])
        ]
        ctx.top_hypothesis = ctx.hypotheses[0] if ctx.hypotheses else None
        ctx.proposed_patch = cp.get("proposed_patch")
        ctx.changed_files = cp.get("changed_files", [])
        ctx.test_passed = cp.get("test_passed", False)
        ctx.pull_request_url = cp.get("pull_request_url")
        ctx.security_findings = cp.get("security_findings", [])
        ctx.total_model_calls = cp.get("total_model_calls", 0)
        ctx.scratchpad = cp.get("scratchpad", {})
        return ctx
