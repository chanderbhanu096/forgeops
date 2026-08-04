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
    confidence: float
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
    mission_id: uuid.UUID
    title: str
    description: str
    attachments: list[dict[str, Any]] = field(default_factory=list)

    plan: list[PlanStep] = field(default_factory=list)
    current_plan_step: int = 0

    repository_url: str | None = None
    repository_path: str | None = None
    environment_summary: str = ""

    raw_evidence: list[dict[str, Any]] = field(default_factory=list)
    relevant_files: list[str] = field(default_factory=list)
    log_excerpts: list[str] = field(default_factory=list)

    hypotheses: list[Hypothesis] = field(default_factory=list)
    top_hypothesis: Hypothesis | None = None
    verification_results: list[VerificationResult] = field(default_factory=list)

    proposed_patch: str | None = None
    changed_files: list[str] = field(default_factory=list)
    sandbox_test_output: str | None = None
    test_passed: bool = False
    security_findings: list[dict[str, Any]] = field(default_factory=list)

    pull_request_url: str | None = None
    pull_request_number: int | None = None

    last_cost_usd: float = 0.0
    total_model_calls: int = 0
    conversation: list[dict[str, Any]] = field(default_factory=list)
    scratchpad: dict[str, Any] = field(default_factory=dict)

    @classmethod
    async def from_mission(cls, mission: Mission) -> MissionContext:
        if mission.checkpoint:
            return cls._from_checkpoint(mission.checkpoint, mission)
        return cls(
            mission_id=mission.id,
            title=mission.title,
            description=mission.description,
            attachments=mission.attachments or [],
        )

    def to_checkpoint(self) -> dict[str, Any]:
        """Serialise every recruiter-visible field to a JSON-safe checkpoint."""
        return {
            "mission_id": str(self.mission_id),
            "title": self.title,
            "description": self.description,
            "attachments": self.attachments,
            "plan": [
                {
                    "step_id": step.step_id,
                    "description": step.description,
                    "skill_name": step.skill_name,
                    "estimated_cost_usd": step.estimated_cost_usd,
                    "completed": step.completed,
                }
                for step in self.plan
            ],
            "current_plan_step": self.current_plan_step,
            "repository_url": self.repository_url,
            "repository_path": self.repository_path,
            "environment_summary": self.environment_summary,
            "raw_evidence": self.raw_evidence,
            "relevant_files": self.relevant_files,
            "log_excerpts": self.log_excerpts,
            "hypotheses": [
                {
                    "id": hypothesis.id,
                    "description": hypothesis.description,
                    "confidence": hypothesis.confidence,
                    "evidence": hypothesis.evidence,
                    "rank": hypothesis.rank,
                }
                for hypothesis in self.hypotheses
            ],
            "verification_results": [
                {
                    "hypothesis_id": result.hypothesis_id,
                    "confirmed": result.confirmed,
                    "confidence": result.confidence,
                    "findings": result.findings,
                }
                for result in self.verification_results
            ],
            "proposed_patch": self.proposed_patch,
            "changed_files": self.changed_files,
            "sandbox_test_output": self.sandbox_test_output,
            "test_passed": self.test_passed,
            "pull_request_url": self.pull_request_url,
            "pull_request_number": self.pull_request_number,
            "security_findings": self.security_findings,
            "last_cost_usd": self.last_cost_usd,
            "total_model_calls": self.total_model_calls,
            "conversation": self.conversation,
            "scratchpad": self.scratchpad,
        }

    def to_checkpoint_metadata(self) -> dict[str, Any]:
        return {
            "plan_step": self.current_plan_step,
            "total_plan_steps": len(self.plan),
            "evidence_count": len(self.raw_evidence),
            "hypothesis_count": len(self.hypotheses),
            "has_patch": self.proposed_patch is not None,
            "test_passed": self.test_passed,
        }

    def update(self, result: dict[str, Any] | None) -> None:
        if not result:
            return
        for key, value in result.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def add_evidence(
        self, source: str, content: str, metadata: dict[str, Any] | None = None
    ) -> None:
        self.raw_evidence.append(
            {
                "source": source,
                "content": content,
                "metadata": metadata or {},
            }
        )

    def add_model_cost(self, cost_usd: float) -> None:
        self.last_cost_usd = cost_usd
        self.total_model_calls += 1

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
                step_id=step["step_id"],
                description=step["description"],
                skill_name=step.get("skill_name"),
                estimated_cost_usd=step.get("estimated_cost_usd", 0.0),
                completed=step.get("completed", False),
            )
            for step in cp.get("plan", [])
        ]
        ctx.current_plan_step = cp.get("current_plan_step", 0)
        ctx.repository_url = cp.get("repository_url")
        ctx.repository_path = cp.get("repository_path")
        ctx.environment_summary = cp.get("environment_summary", "")
        ctx.raw_evidence = cp.get("raw_evidence", [])
        ctx.relevant_files = cp.get("relevant_files", [])
        ctx.log_excerpts = cp.get("log_excerpts", [])
        ctx.hypotheses = [
            Hypothesis(
                id=hypothesis["id"],
                description=hypothesis["description"],
                confidence=hypothesis["confidence"],
                evidence=hypothesis.get("evidence", []),
                rank=hypothesis.get("rank", 0),
            )
            for hypothesis in cp.get("hypotheses", [])
        ]
        ctx.top_hypothesis = ctx.hypotheses[0] if ctx.hypotheses else None
        ctx.verification_results = [
            VerificationResult(
                hypothesis_id=result["hypothesis_id"],
                confirmed=result["confirmed"],
                confidence=result["confidence"],
                findings=result.get("findings", []),
            )
            for result in cp.get("verification_results", [])
        ]
        ctx.proposed_patch = cp.get("proposed_patch")
        ctx.changed_files = cp.get("changed_files", [])
        ctx.sandbox_test_output = cp.get("sandbox_test_output")
        ctx.test_passed = cp.get("test_passed", False)
        ctx.pull_request_url = cp.get("pull_request_url")
        ctx.pull_request_number = cp.get("pull_request_number")
        ctx.security_findings = cp.get("security_findings", [])
        ctx.last_cost_usd = cp.get("last_cost_usd", 0.0)
        ctx.total_model_calls = cp.get("total_model_calls", 0)
        ctx.conversation = cp.get("conversation", [])
        ctx.scratchpad = cp.get("scratchpad", {})
        return ctx
