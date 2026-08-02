"""
Verifier pipeline — the enforcement gate between solution generation
and human approval.

Architecture:
    patch / SQL / terraform
          ↓
    VerificationPipeline.run(payload)
          ↓
    Ordered list of Verifier objects
    Each returns a VerifierResult (passed, findings, severity)
          ↓
    PipelineResult aggregates: overall pass/fail, all findings,
    total cost, recommendation for the runtime

Every verifier is:
    - Deterministic (same input → same verdict)
    - Read-only (never modifies the patch)
    - Independent (no shared mutable state)
    - Fast-fail optional (critical failures short-circuit the pipeline)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class Severity(StrEnum):
    info = "info"
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


@dataclass(frozen=True)
class Finding:
    """A single issue identified by a verifier."""
    verifier: str
    severity: Severity
    title: str
    detail: str
    location: str | None = None   # file:line if known


@dataclass
class VerifierResult:
    verifier_name: str
    passed: bool
    findings: list[Finding] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def critical_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == Severity.critical)

    @property
    def high_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == Severity.high)


@dataclass
class PipelineResult:
    """Aggregated result across the entire verifier pipeline."""
    passed: bool
    results: list[VerifierResult] = field(default_factory=list)

    @property
    def all_findings(self) -> list[Finding]:
        findings: list[Finding] = []
        for r in self.results:
            findings.extend(r.findings)
        return findings

    @property
    def critical_count(self) -> int:
        return sum(1 for f in self.all_findings if f.severity == Severity.critical)

    @property
    def high_count(self) -> int:
        return sum(1 for f in self.all_findings if f.severity == Severity.high)

    @property
    def summary(self) -> str:
        total = len(self.all_findings)
        if self.passed:
            return f"All checks passed ({total} finding(s))"
        return (
            f"Verification FAILED — {self.critical_count} critical, "
            f"{self.high_count} high, {total} total finding(s)"
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "summary": self.summary,
            "critical_count": self.critical_count,
            "high_count": self.high_count,
            "findings": [
                {
                    "verifier": f.verifier,
                    "severity": f.severity,
                    "title": f.title,
                    "detail": f.detail,
                    "location": f.location,
                }
                for f in self.all_findings
            ],
            "verifiers": [
                {
                    "name": r.verifier_name,
                    "passed": r.passed,
                    "findings": len(r.findings),
                }
                for r in self.results
            ],
        }
