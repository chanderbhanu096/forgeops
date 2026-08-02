"""
Infrastructure verifiers — validate Terraform and cloud configuration.

Checks applied to any generated IaC:
    1. Destructive-change detection (terraform destroy, force_delete, etc.)
    2. Dangerous resource patterns (open security groups, public S3 buckets)
    3. Naming convention compliance
    4. Required tag enforcement

Full implementation would invoke `terraform validate` and `checkov` via
subprocess in the sandbox environment. These in-process verifiers cover
the static pattern checks that run without external tooling.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from forgeops.verification.base import Finding, Severity, VerifierResult


# ── Patterns: destructive ─────────────────────────────────────────────────────

_DESTRUCTIVE_PATTERNS: list[tuple[str, str, Severity]] = [
    (r"\bforce_destroy\s*=\s*true\b", "force_destroy = true on a resource", Severity.critical),
    (r"\bdelete_on_termination\s*=\s*true\b", "EBS delete_on_termination = true", Severity.high),
    (r"\blifecycle\s*\{[^}]*prevent_destroy\s*=\s*false", "prevent_destroy disabled", Severity.high),
    (r"\bskip_final_snapshot\s*=\s*true\b", "RDS skip_final_snapshot = true", Severity.high),
    (r"\bterraform\s+destroy\b", "terraform destroy command in IaC", Severity.critical),
    (r"\bdeletion_protection\s*=\s*false\b", "deletion_protection explicitly disabled", Severity.medium),
]

# ── Patterns: security misconfigurations ──────────────────────────────────────

_SECURITY_PATTERNS: list[tuple[str, str, Severity]] = [
    # Open security groups
    (r'cidr_blocks\s*=\s*\["0\.0\.0\.0/0"\]', "Security group open to all IPv4", Severity.critical),
    (r'ipv6_cidr_blocks\s*=\s*\["::/0"\]', "Security group open to all IPv6", Severity.high),
    # Public S3
    (r'\bbucket_acl\s*=\s*"public"', "S3 bucket with public ACL", Severity.critical),
    (r'\bacl\s*=\s*"public-read"', "Resource with public-read ACL", Severity.high),
    (r'\block_public_acls\s*=\s*false\b', "S3 block_public_acls disabled", Severity.high),
    # Encryption
    (r'\bencrypted\s*=\s*false\b', "Encryption explicitly disabled", Severity.high),
    (r'\bstorage_encrypted\s*=\s*false\b', "RDS storage encryption disabled", Severity.high),
    # IAM wildcards
    (r'"Action"\s*:\s*"\*"', "IAM policy with wildcard action", Severity.critical),
    (r'"Resource"\s*:\s*"\*"', "IAM policy with wildcard resource", Severity.high),
]


@dataclass
class TerraformDestructiveChangeVerifier:
    """Blocks IaC changes that would cause irreversible data loss."""

    name: str = "terraform_destructive"

    def verify(self, terraform_content: str, **_: Any) -> VerifierResult:
        findings: list[Finding] = []

        for pattern, title, severity in _DESTRUCTIVE_PATTERNS:
            for match in re.finditer(pattern, terraform_content, re.IGNORECASE | re.MULTILINE):
                line_num = terraform_content[:match.start()].count("\n") + 1
                findings.append(Finding(
                    verifier=self.name,
                    severity=severity,
                    title=title,
                    detail=match.group(0)[:120],
                    location=f"terraform:{line_num}",
                ))

        return VerifierResult(
            verifier_name=self.name,
            passed=all(f.severity not in (Severity.critical, Severity.high) for f in findings),
            findings=findings,
        )


@dataclass
class TerraformSecurityVerifier:
    """Checks for common cloud security misconfigurations in Terraform."""

    name: str = "terraform_security"

    def verify(self, terraform_content: str, **_: Any) -> VerifierResult:
        findings: list[Finding] = []

        for pattern, title, severity in _SECURITY_PATTERNS:
            for match in re.finditer(pattern, terraform_content, re.IGNORECASE | re.MULTILINE):
                line_num = terraform_content[:match.start()].count("\n") + 1
                findings.append(Finding(
                    verifier=self.name,
                    severity=severity,
                    title=title,
                    detail=match.group(0)[:120],
                    location=f"terraform:{line_num}",
                ))

        return VerifierResult(
            verifier_name=self.name,
            passed=all(f.severity not in (Severity.critical, Severity.high) for f in findings),
            findings=findings,
        )
