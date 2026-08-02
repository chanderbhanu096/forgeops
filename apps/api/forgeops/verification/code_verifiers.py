"""
Code verifiers — analyse patches and generated Python code.

Verifiers in this module run entirely in-process (no subprocess) for
speed and portability. They do not require ruff or mypy to be installed
in the host environment; they use Python's built-in AST module for
structural analysis and implement regex-based pattern matching for
secret detection and dangerous-call detection.

When the sandbox service is available, the CodeExecutionVerifier
delegates to it for actual test execution.
"""
from __future__ import annotations

import ast
import re
import textwrap
from dataclasses import dataclass
from typing import Any

from forgeops.verification.base import Finding, Severity, VerifierResult


# ── Helpers ───────────────────────────────────────────────────────────────────


def _extract_python_from_patch(patch: str) -> dict[str, str]:
    """
    Parse a unified diff and return {filename: new_content} for Python files.
    Only the '+' lines (added/modified) are included.
    """
    files: dict[str, str] = {}
    current_file: str | None = None
    current_lines: list[str] = []

    for line in patch.splitlines():
        if line.startswith("+++ b/"):
            # Flush previous
            if current_file and current_lines:
                files[current_file] = "\n".join(current_lines)
            current_file = line[6:].strip()
            current_lines = []
        elif line.startswith("+") and not line.startswith("+++"):
            current_lines.append(line[1:])
        elif line.startswith(" "):
            current_lines.append(line[1:])

    if current_file and current_lines:
        files[current_file] = "\n".join(current_lines)

    return {k: v for k, v in files.items() if k.endswith(".py")}


# ── 1. Syntax verifier ────────────────────────────────────────────────────────


@dataclass
class PatchSyntaxVerifier:
    """Verifies that all Python files in a patch are syntactically valid."""

    name: str = "patch_syntax"

    def verify(self, patch: str, **_: Any) -> VerifierResult:
        findings: list[Finding] = []
        python_files = _extract_python_from_patch(patch)

        if not python_files:
            return VerifierResult(
                verifier_name=self.name,
                passed=True,
                metadata={"python_files_found": 0},
            )

        for filename, content in python_files.items():
            try:
                ast.parse(content)
            except SyntaxError as exc:
                findings.append(Finding(
                    verifier=self.name,
                    severity=Severity.critical,
                    title="Syntax error in generated code",
                    detail=str(exc),
                    location=f"{filename}:{exc.lineno}",
                ))

        return VerifierResult(
            verifier_name=self.name,
            passed=len(findings) == 0,
            findings=findings,
            metadata={"python_files_checked": len(python_files)},
        )


# ── 2. Dangerous pattern verifier ─────────────────────────────────────────────

# Patterns that should never appear in agent-generated code
_DANGEROUS_PATTERNS: list[tuple[str, str, Severity]] = [
    # (pattern, title, severity)
    (r"\bos\.system\s*\(", "os.system() call", Severity.critical),
    (r"\bsubprocess\.call\s*\(.*shell\s*=\s*True", "subprocess with shell=True", Severity.critical),
    (r"\beval\s*\(", "eval() call", Severity.critical),
    (r"\bexec\s*\(", "exec() call", Severity.critical),
    (r"\b__import__\s*\(", "Dynamic __import__ call", Severity.high),
    (r"open\s*\([^)]*['\"]w['\"]", "File write operation", Severity.high),
    (r"\bpickle\.loads?\s*\(", "pickle deserialization", Severity.high),
    (r"\bshutil\.rmtree\s*\(", "shutil.rmtree (recursive delete)", Severity.high),
    (r"\bos\.remove\s*\(", "os.remove call", Severity.medium),
    (r"\brequests\.get\s*\([^)]*verify\s*=\s*False", "SSL verification disabled", Severity.medium),
]

# Secret patterns — likely credentials hard-coded in the patch
_SECRET_PATTERNS: list[tuple[str, str]] = [
    (r"(?i)(api[_-]?key|apikey)\s*=\s*['\"][A-Za-z0-9_\-]{16,}['\"]", "Possible API key"),
    (r"(?i)(password|passwd|pwd)\s*=\s*['\"][^'\"]{4,}['\"]", "Possible hard-coded password"),
    (r"(?i)(secret[_-]?key|secret)\s*=\s*['\"][A-Za-z0-9_\-]{16,}['\"]", "Possible secret key"),
    (r"(?i)(aws_access_key_id)\s*=\s*['\"][A-Z0-9]{20}['\"]", "Possible AWS access key"),
    (r"(?i)(aws_secret_access_key)\s*=\s*['\"][A-Za-z0-9/+]{40}['\"]", "Possible AWS secret"),
]


@dataclass
class DangerousPatternVerifier:
    """Scans the raw patch text for dangerous function calls and secret leakage."""

    name: str = "dangerous_patterns"

    def verify(self, patch: str, **_: Any) -> VerifierResult:
        findings: list[Finding] = []

        for pattern, title, severity in _DANGEROUS_PATTERNS:
            for match in re.finditer(pattern, patch, re.MULTILINE):
                line_num = patch[:match.start()].count("\n") + 1
                findings.append(Finding(
                    verifier=self.name,
                    severity=severity,
                    title=title,
                    detail=match.group(0)[:120],
                    location=f"patch:{line_num}",
                ))

        for pattern, title in _SECRET_PATTERNS:
            for match in re.finditer(pattern, patch, re.MULTILINE):
                line_num = patch[:match.start()].count("\n") + 1
                findings.append(Finding(
                    verifier=self.name,
                    severity=Severity.critical,
                    title=f"Potential secret leakage: {title}",
                    detail="Redacted — matched secret pattern",
                    location=f"patch:{line_num}",
                ))

        return VerifierResult(
            verifier_name=self.name,
            passed=all(f.severity not in (Severity.critical, Severity.high) for f in findings),
            findings=findings,
        )


# ── 3. Import verifier ────────────────────────────────────────────────────────

# Modules that must not appear in generated code
_BLOCKED_IMPORTS: set[str] = {
    "subprocess", "socket", "ftplib", "telnetlib",
    "ctypes", "cffi", "multiprocessing",
}

# Modules that are allowed but should be flagged for review
_SUSPICIOUS_IMPORTS: set[str] = {
    "requests", "httpx", "urllib", "urllib2", "urllib3",
    "paramiko", "fabric",
}


@dataclass
class ImportVerifier:
    """Inspects AST import statements for blocked or suspicious modules."""

    name: str = "import_check"

    def verify(self, patch: str, **_: Any) -> VerifierResult:
        findings: list[Finding] = []
        python_files = _extract_python_from_patch(patch)

        for filename, content in python_files.items():
            try:
                tree = ast.parse(content)
            except SyntaxError:
                continue  # syntax verifier will catch this

            for node in ast.walk(tree):
                module: str | None = None
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        module = alias.name.split(".")[0]
                        self._check_module(module, filename, node.lineno, findings)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        module = node.module.split(".")[0]
                        self._check_module(module, filename, node.lineno, findings)

        return VerifierResult(
            verifier_name=self.name,
            passed=all(f.severity != Severity.critical for f in findings),
            findings=findings,
        )

    def _check_module(
        self,
        module: str,
        filename: str,
        lineno: int,
        findings: list[Finding],
    ) -> None:
        if module in _BLOCKED_IMPORTS:
            findings.append(Finding(
                verifier=self.name,
                severity=Severity.critical,
                title=f"Blocked import: {module}",
                detail=f"Module '{module}' is not permitted in generated code",
                location=f"{filename}:{lineno}",
            ))
        elif module in _SUSPICIOUS_IMPORTS:
            findings.append(Finding(
                verifier=self.name,
                severity=Severity.medium,
                title=f"Network-capable import: {module}",
                detail=f"Module '{module}' has network access — verify intent",
                location=f"{filename}:{lineno}",
            ))


# ── 4. Patch size verifier ────────────────────────────────────────────────────


@dataclass
class PatchSizeVerifier:
    """Flags unexpectedly large patches that may indicate unintended changes."""

    name: str = "patch_size"
    max_changed_lines: int = 500
    max_changed_files: int = 20

    def verify(self, patch: str, changed_files: list[str] | None = None, **_: Any) -> VerifierResult:
        findings: list[Finding] = []
        changed_lines = sum(
            1 for line in patch.splitlines()
            if line.startswith("+") and not line.startswith("+++")
        )
        file_count = len(changed_files or [])

        if changed_lines > self.max_changed_lines:
            findings.append(Finding(
                verifier=self.name,
                severity=Severity.high,
                title="Patch exceeds line limit",
                detail=(
                    f"Patch adds {changed_lines} lines "
                    f"(limit: {self.max_changed_lines}). "
                    "Large patches increase review burden and regression risk."
                ),
            ))

        if file_count > self.max_changed_files:
            findings.append(Finding(
                verifier=self.name,
                severity=Severity.medium,
                title="Too many files changed",
                detail=(
                    f"Patch modifies {file_count} files "
                    f"(limit: {self.max_changed_files})."
                ),
            ))

        return VerifierResult(
            verifier_name=self.name,
            passed=all(f.severity != Severity.critical for f in findings),
            findings=findings,
            metadata={
                "changed_lines": changed_lines,
                "changed_files": file_count,
            },
        )
