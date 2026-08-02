"""
Verification pipeline orchestrator.

Composes verifier chains for each payload type (code patch, SQL, IaC)
and runs them in order, collecting results into a PipelineResult.

Design rules:
    - Critical findings in any verifier short-circuit the pipeline
      for that payload type (subsequent verifiers still run unless
      fast_fail=True on the pipeline call).
    - Each verifier is independent — they receive only the inputs
      they declare, extracted from the payload.
    - The pipeline does not modify the payload.
"""
from __future__ import annotations

import asyncio
from typing import Any

import structlog

from forgeops.observability import trace_verification
from forgeops.verification.base import PipelineResult, Severity, VerifierResult
from forgeops.verification.code_verifiers import (
    DangerousPatternVerifier,
    ImportVerifier,
    PatchSizeVerifier,
    PatchSyntaxVerifier,
)
from forgeops.verification.infra_verifiers import (
    TerraformDestructiveChangeVerifier,
    TerraformSecurityVerifier,
)
from forgeops.verification.sql_verifiers import (
    SQLInjectionVerifier,
    SQLRiskVerifier,
    SQLRowLimitVerifier,
    SQLStatementTypeVerifier,
)

log = structlog.get_logger(__name__)


class VerificationPipeline:
    """
    Entry point for all verification.

    Usage::
        pipeline = VerificationPipeline()

        # Verify a code patch
        result = await pipeline.verify_patch(patch, changed_files=[...])
        if not result.passed:
            raise VerificationError(result.summary)

        # Verify a SQL statement
        result = await pipeline.verify_sql(sql)

        # Verify Terraform
        result = await pipeline.verify_terraform(tf_content)
    """

    def __init__(self) -> None:
        # Code verifiers — ordered by severity of what they catch
        self._patch_verifiers = [
            PatchSyntaxVerifier(),
            DangerousPatternVerifier(),
            ImportVerifier(),
            PatchSizeVerifier(),
        ]

        # SQL verifiers
        self._sql_verifiers = [
            SQLStatementTypeVerifier(),
            SQLInjectionVerifier(),
            SQLRowLimitVerifier(),
            SQLRiskVerifier(),   # last — informational
        ]

        # IaC verifiers
        self._terraform_verifiers = [
            TerraformDestructiveChangeVerifier(),
            TerraformSecurityVerifier(),
        ]

    # ── Public API ────────────────────────────────────────────────────────────

    async def verify_patch(
        self,
        patch: str,
        changed_files: list[str] | None = None,
        fast_fail: bool = False,
    ) -> PipelineResult:
        """Run all code verifiers against a unified diff."""
        return await self._run(
            verifiers=self._patch_verifiers,
            payload={"patch": patch, "changed_files": changed_files or []},
            fast_fail=fast_fail,
            pipeline_name="patch",
        )

    async def verify_sql(
        self,
        sql: str,
        max_rows: int = 10_000,
        fast_fail: bool = True,
    ) -> PipelineResult:
        """Run all SQL verifiers. Fast-fail by default — dangerous SQL stops immediately."""
        return await self._run(
            verifiers=self._sql_verifiers,
            payload={"sql": sql, "max_rows": max_rows},
            fast_fail=fast_fail,
            pipeline_name="sql",
        )

    async def verify_terraform(
        self,
        terraform_content: str,
        fast_fail: bool = False,
    ) -> PipelineResult:
        """Run IaC verifiers against Terraform HCL content."""
        return await self._run(
            verifiers=self._terraform_verifiers,
            payload={"terraform_content": terraform_content},
            fast_fail=fast_fail,
            pipeline_name="terraform",
        )

    # ── Internals ─────────────────────────────────────────────────────────────

    async def _run(
        self,
        verifiers: list[Any],
        payload: dict[str, Any],
        fast_fail: bool,
        pipeline_name: str,
    ) -> PipelineResult:
        results: list[VerifierResult] = []
        overall_passed = True

        for verifier in verifiers:
            try:
                # Run synchronously in a thread so we don't block the event loop
                result = await asyncio.get_event_loop().run_in_executor(
                    None, lambda v=verifier: v.verify(**payload)
                )
            except Exception as exc:
                log.error(
                    "verifier_error",
                    verifier=getattr(verifier, "name", str(verifier)),
                    error=str(exc),
                )
                result = VerifierResult(
                    verifier_name=getattr(verifier, "name", "unknown"),
                    passed=False,
                    metadata={"error": str(exc)},
                )

            results.append(result)

            if not result.passed:
                overall_passed = False
                log.warning(
                    "verifier_failed",
                    pipeline=pipeline_name,
                    verifier=result.verifier_name,
                    findings=len(result.findings),
                    critical=result.critical_count,
                    high=result.high_count,
                )
                if fast_fail and result.critical_count > 0:
                    log.info(
                        "pipeline_fast_fail",
                        pipeline=pipeline_name,
                        verifier=result.verifier_name,
                    )
                    break

        pipeline_result = PipelineResult(passed=overall_passed, results=results)
        all_findings = pipeline_result.all_findings
        log.info(
            "pipeline_complete",
            pipeline=pipeline_name,
            passed=pipeline_result.passed,
            total_findings=len(all_findings),
        )
        trace_verification(
            pipeline=pipeline_name,
            passed=pipeline_result.passed,
            critical_count=sum(f.severity == Severity.critical for f in all_findings),
            high_count=sum(f.severity == Severity.high for f in all_findings),
            total_findings=len(all_findings),
        )
        return pipeline_result


# ── Singleton ─────────────────────────────────────────────────────────────────

_pipeline: VerificationPipeline | None = None


def get_pipeline() -> VerificationPipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = VerificationPipeline()
    return _pipeline
